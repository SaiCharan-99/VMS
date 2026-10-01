from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from pathlib import Path, PurePath
from typing import BinaryIO

import cv2
from sqlalchemy import Select, exists, func, or_, select
from sqlalchemy.orm import Session

from vms.db.models import (
    Analysis,
    FinalStatus,
    Job,
    ProcessType,
    Role,
    User,
    Video,
    VideoSource,
    new_uuid,
    utcnow,
)
from vms.services import audit, jobs
from vms.storage import Storage, TooLargeError

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv"}


class UploadRejectedError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass
class UploadOutcome:
    video: Video
    job: Job | None
    duplicate: bool


def _probe_duration(path: Path) -> float | None:
    """None when OpenCV can't decode a single frame; otherwise the duration (0 if unknown)."""
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened() or not cap.read()[0]:
            return None
        fps = cap.get(cv2.CAP_PROP_FPS) or 0.0
        frames = cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0.0
        return round(frames / fps, 2) if fps > 0 else 0.0
    finally:
        cap.release()


def create_from_upload(
    session: Session,
    storage: Storage,
    fileobj: BinaryIO,
    filename: str,
    process_type: ProcessType,
    *,
    user: User | None,
    source: VideoSource,
    max_bytes: int,
    content_type: str | None = None,
    awb: str | None = None,
    order_ref: str | None = None,
    station_id: int | None = None,
    enqueue: bool = True,
    max_attempts: int = 3,
) -> UploadOutcome:
    """Stream to storage, hash, dedupe on sha256, check OpenCV can decode it, enqueue a job."""
    name = PurePath(filename or "").name
    ext = PurePath(name).suffix.lower()
    if not name:
        raise UploadRejectedError(400, "No file selected.")
    if ext not in ALLOWED_EXTENSIONS:
        raise UploadRejectedError(
            400, f"Unsupported file type: {ext or '(none)'}. Allowed: {sorted(ALLOWED_EXTENSIONS)}"
        )

    video_uuid = new_uuid()
    now = utcnow()
    key = f"videos/{now:%Y}/{now:%m}/{video_uuid}{ext}"
    try:
        size, sha256 = storage.save_stream(key, fileobj, max_bytes=max_bytes)
    except TooLargeError as exc:
        raise UploadRejectedError(413, f"File too large (limit {max_bytes} bytes).") from exc

    existing = session.scalar(
        select(Video)
        .where(Video.sha256 == sha256, Video.deleted_at.is_(None))
        .order_by(Video.id)
        .limit(1)
    )
    if existing is not None:
        storage.delete(key)
        return UploadOutcome(existing, jobs.latest_job(session, existing.id), duplicate=True)

    duration = _probe_duration(storage.path(key))
    if duration is None:
        storage.delete(key)
        raise UploadRejectedError(400, "File is not a readable video.")

    video = Video(
        uuid=video_uuid,
        original_filename=name,
        storage_key=key,
        sha256=sha256,
        size_bytes=size,
        content_type=content_type,
        process_type=process_type,
        awb=awb or None,
        order_ref=order_ref or None,
        uploaded_by=user.id if user else None,
        station_id=station_id,
        source=source,
        duration_s=duration or None,
        created_at=now,
    )
    session.add(video)
    session.flush()
    job = jobs.enqueue(session, video, max_attempts) if enqueue else None
    audit.log(
        session,
        "video.uploaded",
        "video",
        video.id,
        {"filename": name, "sha256": sha256, "size_bytes": size, "source": source.value},
        actor_user_id=user.id if user else None,
    )
    return UploadOutcome(video, job, duplicate=False)


@dataclass
class VideoFilters:
    status: FinalStatus | None = None
    process_type: ProcessType | None = None
    awb: str | None = None
    q: str | None = None
    station_id: int | None = None
    uploaded_by: int | None = None
    date_from: date | None = None
    date_to: date | None = None  # inclusive


SORTS = {
    "created_at": Video.created_at.asc(),
    "-created_at": Video.created_at.desc(),
    "awb": Video.awb.asc(),
    "-awb": Video.awb.desc(),
    "final_status": Video.final_status.asc(),
    "-final_status": Video.final_status.desc(),
}


def list_query(filters: VideoFilters, user: User, sort: str = "-created_at") -> Select:
    stmt = select(Video).where(Video.deleted_at.is_(None))
    if user.role == Role.operator:
        stmt = stmt.where(Video.uploaded_by == user.id)
    if filters.status:
        stmt = stmt.where(Video.final_status == filters.status)
    if filters.process_type:
        stmt = stmt.where(Video.process_type == filters.process_type)
    if filters.awb:
        stmt = stmt.where(Video.awb == filters.awb)
    if filters.station_id is not None:
        stmt = stmt.where(Video.station_id == filters.station_id)
    if filters.uploaded_by is not None:
        stmt = stmt.where(Video.uploaded_by == filters.uploaded_by)
    if filters.date_from:
        stmt = stmt.where(Video.created_at >= datetime.combine(filters.date_from, time.min))
    if filters.date_to:
        end = datetime.combine(filters.date_to + timedelta(days=1), time.min)
        stmt = stmt.where(Video.created_at < end)
    if filters.q:
        like = f"%{filters.q.strip().lower()}%"
        barcode_hit = exists().where(
            Analysis.video_id == Video.id, func.lower(Analysis.barcodes).like(like)
        )
        stmt = stmt.where(
            or_(
                func.lower(Video.original_filename).like(like),
                func.lower(Video.awb).like(like),
                func.lower(Video.order_ref).like(like),
                barcode_hit,
            )
        )
    return stmt.order_by(SORTS[sort], Video.id.desc())


def soft_delete(session: Session, video: Video, user: User) -> None:
    video.deleted_at = utcnow()
    audit.log(session, "video.deleted", "video", video.id, actor_user_id=user.id)


def reanalyze(session: Session, video: Video, user: User, max_attempts: int = 3) -> Job:
    job = jobs.enqueue(session, video, max_attempts)
    audit.log(
        session, "video.reanalyze", "video", video.id, {"job_id": job.id}, actor_user_id=user.id
    )
    return job
