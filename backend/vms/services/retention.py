"""Retention: delete old video files but keep every row, analysis and evidence frame.

A file is kept while its video is still open (pending or awaiting human review), disputed,
or has a queued/running job, whatever its age.
"""

from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from vms.db.models import FinalStatus, Job, JobStatus, Video, utcnow
from vms.services import audit
from vms.storage import Storage

OPEN_STATUSES = (FinalStatus.pending, FinalStatus.review)


@dataclass
class PurgeReport:
    purged: int
    bytes_freed: int
    video_ids: list[int]


def candidates(session: Session, older_than_days: int) -> list[Video]:
    cutoff = utcnow() - timedelta(days=older_than_days)
    active_job = exists().where(
        Job.video_id == Video.id, Job.status.in_((JobStatus.queued, JobStatus.running))
    )
    return list(
        session.scalars(
            select(Video)
            .where(
                Video.created_at < cutoff,
                Video.storage_key.is_not(None),
                Video.file_purged_at.is_(None),
                Video.disputed_at.is_(None),
                Video.final_status.not_in(OPEN_STATUSES),
                ~active_job,
            )
            .order_by(Video.id)
        )
    )


def purge(
    session: Session, storage: Storage, older_than_days: int, *, dry_run: bool = False
) -> PurgeReport:
    if older_than_days < 1:
        raise ValueError("older_than_days must be at least 1")
    videos = candidates(session, older_than_days)
    freed = 0
    for video in videos:
        size = video.size_bytes or 0
        freed += size
        if dry_run:
            continue
        storage.delete(video.storage_key)
        video.file_purged_at = utcnow()
        audit.log(
            session,
            "video.file_purged",
            "video",
            video.id,
            {"older_than_days": older_than_days, "size_bytes": size},
        )
        session.commit()  # per video, so a crash never leaves rows claiming deleted files exist
    return PurgeReport(len(videos), freed, [v.id for v in videos])
