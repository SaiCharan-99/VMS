"""Turn human reviews into an eval labels file (every reviewed video becomes eval data)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.db.models import Review, Video
from vms.evaluation.labels import LabelRow
from vms.storage import get_storage


def export_reviewed(session: Session) -> tuple[list[LabelRow], int]:
    """(rows, skipped). The latest review per video wins; videos whose file is gone are skipped."""
    storage = get_storage()
    latest: dict[int, Review] = {}
    for review in session.scalars(select(Review).order_by(Review.id)):
        latest[review.video_id] = review
    rows, skipped = [], 0
    for video_id, review in latest.items():
        video = session.get(Video, video_id)
        if (
            video is None
            or video.deleted_at
            or not video.storage_key
            or not storage.exists(video.storage_key)
        ):
            skipped += 1
            continue
        rows.append(
            LabelRow(
                video=storage.path(video.storage_key),
                process_type=video.process_type.value,
                expected_status=review.final_status.value,
                notes=f"review:{review.reason_code}; video:{video.uuid}",
            )
        )
    return rows, skipped
