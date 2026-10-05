"""DB-backed job queue (IMPLEMENTATION.md §7). Every state change is guarded by `worker_id`,
so a worker that lost its job (re-queued as stale) can never overwrite someone else's run."""

from datetime import timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from vms.db.models import Job, JobStatus, Video, utcnow


def enqueue(session: Session, video: Video, max_attempts: int = 3) -> Job:
    job = Job(video=video, status=JobStatus.queued, max_attempts=max_attempts)
    session.add(job)
    session.flush()
    return job


def latest_job(session: Session, video_id: int) -> Job | None:
    return session.scalar(
        select(Job).where(Job.video_id == video_id).order_by(Job.id.desc()).limit(1)
    )


def _claim_values(worker_id: str) -> dict:
    now = utcnow()
    return {
        "status": JobStatus.running,
        "worker_id": worker_id,
        "attempts": Job.attempts + 1,
        "progress": 0.0,
        "error": None,
        "started_at": now,
        "heartbeat_at": now,
    }


def claim_next(session: Session, worker_id: str) -> Job | None:
    """Atomically take the oldest queued job. Commits, so the claim is visible at once."""
    if session.get_bind().dialect.name == "postgresql":
        return _claim_skip_locked(session, worker_id)
    while True:
        job_id = session.scalar(
            select(Job.id).where(Job.status == JobStatus.queued).order_by(Job.id).limit(1)
        )
        if job_id is None:
            session.rollback()
            return None
        claimed = session.execute(
            update(Job)
            .where(Job.id == job_id, Job.status == JobStatus.queued)
            .values(**_claim_values(worker_id))
            .execution_options(synchronize_session=False)
        ).rowcount
        session.commit()
        if claimed == 1:
            return session.get(Job, job_id, populate_existing=True)
        # Another worker won the race for this row; try the next one.


def _claim_skip_locked(session: Session, worker_id: str) -> Job | None:
    """Postgres: rows another worker is claiming are skipped instead of waited on or retried."""
    job_id = session.scalar(
        select(Job.id)
        .where(Job.status == JobStatus.queued)
        .order_by(Job.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if job_id is None:
        session.rollback()
        return None
    session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(**_claim_values(worker_id))
        .execution_options(synchronize_session=False)
    )
    session.commit()
    return session.get(Job, job_id, populate_existing=True)


def _owned(job_id: int, worker_id: str):  # noqa: ANN202
    return update(Job).where(
        Job.id == job_id, Job.worker_id == worker_id, Job.status == JobStatus.running
    )


def heartbeat(session: Session, job_id: int, worker_id: str, progress: float) -> bool:
    """Record progress. False means this worker no longer owns the job."""
    stmt = _owned(job_id, worker_id).values(
        progress=min(max(progress, 0.0), 1.0), heartbeat_at=utcnow()
    )
    return session.execute(stmt).rowcount == 1


def complete(session: Session, job_id: int, worker_id: str) -> bool:
    now = utcnow()
    stmt = _owned(job_id, worker_id).values(
        status=JobStatus.done, progress=1.0, finished_at=now, heartbeat_at=now
    )
    return session.execute(stmt).rowcount == 1


def fail(session: Session, job_id: int, worker_id: str, error: str) -> bool:
    now = utcnow()
    stmt = _owned(job_id, worker_id).values(
        status=JobStatus.failed, error=error[:2000], finished_at=now, heartbeat_at=now
    )
    return session.execute(stmt).rowcount == 1


def release(session: Session, job_id: int, worker_id: str) -> bool:
    """Put a job back in the queue on graceful shutdown; the attempt doesn't count."""
    stmt = _owned(job_id, worker_id).values(
        status=JobStatus.queued,
        worker_id=None,
        attempts=Job.attempts - 1,
        progress=0.0,
        started_at=None,
        heartbeat_at=None,
    )
    return session.execute(stmt).rowcount == 1


def requeue_stale(session: Session, stale_s: int) -> tuple[int, int]:
    """Re-queue running jobs whose worker went silent; fail them after max_attempts.
    Returns (requeued, failed)."""
    cutoff = utcnow() - timedelta(seconds=stale_s)
    stale = (Job.status == JobStatus.running, Job.heartbeat_at < cutoff)
    requeued = session.execute(
        update(Job)
        .where(*stale, Job.attempts < Job.max_attempts)
        .values(status=JobStatus.queued, worker_id=None, progress=0.0, heartbeat_at=None)
        .execution_options(synchronize_session=False)
    ).rowcount
    failed = session.execute(
        update(Job)
        .where(*stale, Job.attempts >= Job.max_attempts)
        .values(
            status=JobStatus.failed,
            error="Worker stopped responding; gave up after max_attempts.",
            finished_at=utcnow(),
        )
        .execution_options(synchronize_session=False)
    ).rowcount
    return requeued, failed
