"""Human reviews: append-only, the latest one per video wins (IMPLEMENTATION.md §7)."""

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from vms.db.models import FinalStatus, ProcessType, Review, ReviewStatus, Video
from vms.services import analyses, audit
from vms.services.principal import Principal

REASON_CODES = (
    "label_unclear",
    "seal_not_shown",
    "tags_not_shown",
    "product_not_inspected",
    "video_quality",
    "false_negative_model",
    "other",
)


class ReviewError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def create(
    session: Session,
    video: Video,
    reviewer: Principal,
    final_status: ReviewStatus,
    reason_code: str,
    comment: str | None,
) -> Review:
    """Record a decision on the video's latest analysis and update `videos.final_status`.

    A comment is required for `other`, and whenever the reviewer overturns a model pass/fail,
    so every contradiction of the model is explained in the audit trail.
    """
    if reviewer.user is None:
        raise ReviewError(403, "Reviews need a user login.")
    if reason_code not in REASON_CODES:
        raise ReviewError(422, f"Unknown reason_code. Allowed: {list(REASON_CODES)}")
    analysis = analyses.latest_analysis(session, video.id)
    if analysis is None:
        raise ReviewError(409, "This video has no analysis to review yet.")
    comment = (comment or "").strip() or None
    overturns = analysis.status in ("pass", "fail") and analysis.status != final_status.value
    if comment is None and (reason_code == "other" or overturns):
        why = "reason 'other'" if reason_code == "other" else "overturning the model's verdict"
        raise ReviewError(422, f"A comment is required when {why}.")

    review = Review(
        analysis_id=analysis.id,
        video_id=video.id,
        reviewer_id=reviewer.user.id,
        final_status=final_status,
        reason_code=reason_code,
        comment=comment,
    )
    session.add(review)
    session.flush()
    analyses.refresh_final_status(session, video)
    audit.log(
        session,
        "review.created",
        "video",
        video.id,
        {
            "review_id": review.id,
            "analysis_id": analysis.id,
            "model_status": analysis.status,
            "final_status": final_status.value,
            "reason_code": reason_code,
            "comment": comment,
        },
        **reviewer.actor,
    )
    return review


def queue_query(process_type: ProcessType | None = None, station_id: int | None = None) -> Select:
    """Videos waiting for a human, oldest first."""
    stmt = select(Video).where(Video.deleted_at.is_(None), Video.final_status == FinalStatus.review)
    if process_type:
        stmt = stmt.where(Video.process_type == process_type)
    if station_id is not None:
        stmt = stmt.where(Video.station_id == station_id)
    return stmt.order_by(Video.created_at, Video.id)
