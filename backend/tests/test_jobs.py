import threading
from datetime import timedelta

from sqlalchemy import update

from vms.db import session_scope
from vms.db.models import Job, JobStatus, ProcessType, Video, VideoSource, utcnow
from vms.services import jobs


def _queue(n: int, max_attempts: int = 3) -> list[int]:
    with session_scope() as s:
        video = Video(
            original_filename="v.mp4", process_type=ProcessType.Return, source=VideoSource.web
        )
        s.add(video)
        return [jobs.enqueue(s, video, max_attempts).id for _ in range(n)]


def test_claim_takes_oldest_and_counts_attempt(db_ready):
    first, _ = _queue(2)
    with session_scope() as s:
        job = jobs.claim_next(s, "w1")
    assert job.id == first
    assert (job.status, job.worker_id, job.attempts) == (JobStatus.running, "w1", 1)


def test_concurrent_claims_never_share_a_job(db_ready):
    _queue(20)
    claimed: dict[str, list[int]] = {}
    barrier = threading.Barrier(4)

    def worker(name: str) -> None:
        got = claimed.setdefault(name, [])
        barrier.wait()
        while True:
            with session_scope() as s:
                job = jobs.claim_next(s, name)
            if job is None:
                return
            got.append(job.id)

    threads = [threading.Thread(target=worker, args=(f"w{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    all_ids = [i for ids in claimed.values() for i in ids]
    assert len(all_ids) == 20
    assert len(set(all_ids)) == 20


def _age_heartbeat(job_id: int, seconds: int) -> None:
    with session_scope() as s:
        s.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(heartbeat_at=utcnow() - timedelta(seconds=seconds))
        )


def test_stale_job_is_requeued_then_failed_after_max_attempts(db_ready):
    (job_id,) = _queue(1, max_attempts=2)
    for attempt in (1, 2):
        with session_scope() as s:
            job = jobs.claim_next(s, f"w{attempt}")
        assert job.attempts == attempt
        _age_heartbeat(job_id, 600)
        with session_scope() as s:
            requeued, failed = jobs.requeue_stale(s, stale_s=300)
        assert (requeued, failed) == ((1, 0) if attempt == 1 else (0, 1))

    with session_scope() as s:
        job = s.get(Job, job_id)
        assert job.status == JobStatus.failed
        assert "max_attempts" in job.error


def test_fresh_heartbeat_is_not_stale(db_ready):
    _queue(1)
    with session_scope() as s:
        jobs.claim_next(s, "w1")
    with session_scope() as s:
        assert jobs.requeue_stale(s, stale_s=300) == (0, 0)


def test_lost_job_cannot_be_completed_by_old_owner(db_ready):
    (job_id,) = _queue(1)
    with session_scope() as s:
        jobs.claim_next(s, "old")
    _age_heartbeat(job_id, 600)
    with session_scope() as s:
        jobs.requeue_stale(s, stale_s=300)
        jobs.claim_next(s, "new")
    with session_scope() as s:
        assert not jobs.heartbeat(s, job_id, "old", 0.5)
        assert not jobs.complete(s, job_id, "old")
        assert jobs.complete(s, job_id, "new")


def test_release_returns_job_without_counting_attempt(db_ready):
    (job_id,) = _queue(1)
    with session_scope() as s:
        jobs.claim_next(s, "w1")
    with session_scope() as s:
        assert jobs.release(s, job_id, "w1")
    with session_scope() as s:
        job = s.get(Job, job_id)
        assert (job.status, job.attempts, job.worker_id) == (JobStatus.queued, 0, None)
