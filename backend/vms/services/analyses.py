from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.analysis.result import AnalysisResult
from vms.db.models import Analysis, EvidenceItem, FinalStatus, Review, Video
from vms.services import audit


def latest_analysis(session: Session, video_id: int) -> Analysis | None:
    return session.scalar(
        select(Analysis).where(Analysis.video_id == video_id).order_by(Analysis.id.desc()).limit(1)
    )


def refresh_final_status(session: Session, video: Video) -> None:
    """Denormalized status: the latest human review wins over the latest analysis."""
    review = session.scalar(
        select(Review).where(Review.video_id == video.id).order_by(Review.id.desc()).limit(1)
    )
    if review is not None:
        video.final_status = FinalStatus(review.final_status.value)
        return
    analysis = latest_analysis(session, video.id)
    video.final_status = FinalStatus(analysis.status) if analysis else FinalStatus.pending


def save_result(
    session: Session,
    video: Video,
    job_id: int | None,
    result: AnalysisResult,
    analysis_uuid: str,
) -> Analysis:
    """Store a schema 2.0 result plus one evidence row per saved frame, then update the video."""
    analysis = Analysis(
        uuid=analysis_uuid,
        video_id=video.id,
        job_id=job_id,
        schema_version=result.schema_version,
        engine_version=result.engine.version,
        rubric_id=result.rubric_id,
        total_score=result.total_score,
        confidence=result.confidence,
        status=result.status,
        decision=result.decision,
        barcodes=" ".join(b.value for b in result.barcodes),
        result_json=result.model_dump(mode="json"),
    )
    session.add(analysis)
    session.flush()
    for step in result.steps:
        for ev in step.evidence:
            if ev.image:
                session.add(
                    EvidenceItem(
                        analysis_id=analysis.id,
                        step_key=step.key,
                        kind=ev.kind,
                        t_s=ev.t_s,
                        storage_key=ev.image,
                    )
                )

    video.duration_s = result.video.duration_s
    if not video.awb and result.barcodes:
        video.awb = result.barcodes[0].value
    session.flush()
    refresh_final_status(session, video)
    audit.log(
        session,
        "analysis.completed",
        "analysis",
        analysis.id,
        {
            "video_id": video.id,
            "job_id": job_id,
            "status": result.status,
            "total_score": result.total_score,
            "rubric_id": result.rubric_id,
        },
    )
    return analysis
