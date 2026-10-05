"""Job worker: `python -m vms.worker [--once] [--poll 1.5]`.

Polls the jobs table, runs `analyze_video`, and stores the result. Any number of workers can
run at once: claims are atomic, and every write is guarded by this worker's id.
"""

import argparse
import logging
import os
import signal
import socket
import threading
import time
import uuid
from collections.abc import Callable
from types import FrameType

from sqlalchemy import text

from vms.analysis import analyze_video
from vms.config import Settings, get_settings
from vms.db import session_scope
from vms.db.models import Job, Video, new_uuid
from vms.logging import bind_log_context, clear_log_context, configure_logging
from vms.metrics import ANALYSIS_DURATION
from vms.services import analyses, audit, jobs
from vms.storage import Storage, get_storage

log = logging.getLogger(__name__)

HEARTBEAT_EVERY_S = 1.0
HEARTBEAT_FILE_EVERY_S = 10.0


class _Interrupted(Exception):
    """Raised from the progress callback to abandon the current analysis."""


def run_job(
    job_id: int,
    worker_id: str,
    storage: Storage,
    settings: Settings,
    stop: Callable[[], bool] | None = None,
) -> str:
    """Analyze a job this worker has claimed. Returns the final job status
    ("done", "failed", "released" on shutdown, or "lost" if another worker took it over)."""
    with session_scope() as s:
        video = s.get(Video, s.get(Job, job_id).video_id)
        storage_key, process_type = video.storage_key, video.process_type.value
    bind_log_context(job_id=job_id, video_id=video.id, worker_id=worker_id)
    started = time.monotonic()

    def observe(outcome: str) -> None:
        ANALYSIS_DURATION.labels(process_type, outcome).observe(time.monotonic() - started)

    analysis_uuid = new_uuid()
    evidence_key = f"evidence/{analysis_uuid}"
    last_beat = time.monotonic()

    def on_progress(p: float) -> None:
        nonlocal last_beat
        if stop is not None and stop():
            raise _Interrupted("released")
        now = time.monotonic()
        if now - last_beat < HEARTBEAT_EVERY_S and p < 1.0:
            return
        last_beat = now
        with session_scope() as s:
            if not jobs.heartbeat(s, job_id, worker_id, p):
                raise _Interrupted("lost")

    try:
        if storage_key is None:
            raise FileNotFoundError("Video has no stored file (legacy import).")
        result = analyze_video(
            storage.path(storage_key),
            process_type,
            settings=settings,
            evidence_dir=storage.path(evidence_key),
            progress_cb=on_progress,
        )
    except _Interrupted as exc:
        storage.delete(evidence_key)
        if str(exc) == "released":
            with session_scope() as s:
                jobs.release(s, job_id, worker_id)
        return str(exc)
    except Exception as exc:
        storage.delete(evidence_key)
        observe("failed")
        error = f"{type(exc).__name__}: {exc}"
        log.warning("Job %s failed: %s", job_id, error)
        with session_scope() as s:
            if jobs.fail(s, job_id, worker_id, error):
                audit.log(s, "analysis.failed", "job", job_id, {"error": error})
        return "failed"

    with session_scope() as s:
        if not jobs.complete(s, job_id, worker_id):
            s.rollback()
            storage.delete(evidence_key)
            return "lost"
        video = s.get(Video, s.get(Job, job_id).video_id)
        analyses.save_result(s, video, job_id, result, analysis_uuid)
    observe(result.status)
    log.info("Job %s done: %s %s/100", job_id, result.status, result.total_score)
    return "done"


class Worker:
    def __init__(self, settings: Settings | None = None, storage: Storage | None = None) -> None:
        self.settings = settings or get_settings()
        self.storage = storage or get_storage()
        self.worker_id = f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex[:6]}"
        self.stopping = False

    def request_stop(self, signum: int | None = None, _frame: FrameType | None = None) -> None:
        if not self.stopping:
            log.info("Stop requested; releasing the current job and exiting.")
        self.stopping = True

    def run_once(self) -> bool:
        """Re-queue stale jobs, then process at most one job. True if a job was processed."""
        with session_scope() as s:
            requeued, failed = jobs.requeue_stale(s, self.settings.job_stale_s)
        if requeued or failed:
            log.warning("Stale jobs: %d re-queued, %d failed", requeued, failed)
        with session_scope() as s:
            job = jobs.claim_next(s, self.worker_id)
        if job is None:
            return False
        log.info("Claimed job %s (video %s, attempt %s)", job.id, job.video_id, job.attempts)
        try:
            run_job(job.id, self.worker_id, self.storage, self.settings, stop=lambda: self.stopping)
        finally:
            clear_log_context()
        return True

    def _touch_heartbeat(self) -> None:
        """Container liveness: the file's mtime is refreshed while the process (and its
        DB connection) is healthy, including during a long analysis."""
        path = self.settings.worker_heartbeat_file
        while not self.stopping and path is not None:
            try:
                with session_scope() as s:
                    s.execute(text("SELECT 1"))
                path.touch()
            except Exception as exc:  # noqa: BLE001 - a stale file is the signal
                log.warning("Heartbeat check failed: %s", exc)
            time.sleep(HEARTBEAT_FILE_EVERY_S)

    def run(self, poll_s: float) -> None:
        log.info("Worker %s started (poll %.1fs)", self.worker_id, poll_s)
        if self.settings.worker_heartbeat_file is not None:
            threading.Thread(target=self._touch_heartbeat, daemon=True).start()
        while not self.stopping:
            if not self.run_once():
                deadline = time.monotonic() + poll_s
                while not self.stopping and time.monotonic() < deadline:
                    time.sleep(0.1)
        log.info("Worker %s stopped", self.worker_id)


def main(argv: list[str] | None = None) -> int:
    settings = get_settings()
    parser = argparse.ArgumentParser(prog="vms.worker")
    parser.add_argument("--once", action="store_true", help="process at most one job and exit")
    parser.add_argument("--poll", type=float, default=settings.worker_poll_s, help="seconds")
    args = parser.parse_args(argv)
    configure_logging()

    worker = Worker(settings)
    if settings.worker_metrics_port and not args.once:
        from prometheus_client import start_http_server

        from vms.metrics import WORKER_REGISTRY

        start_http_server(settings.worker_metrics_port, registry=WORKER_REGISTRY)
    if args.once:
        worker.run_once()
        return 0
    for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
        if hasattr(signal, name):
            signal.signal(getattr(signal, name), worker.request_stop)
    worker.run(args.poll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
