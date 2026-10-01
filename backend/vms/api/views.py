"""ORM → response model conversions that need URLs or extra lookups."""

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.api.schemas import AnalysisBrief, AnalysisOut, EvidenceOut, VideoOut
from vms.db.models import Analysis, User, Video
from vms.security import sign_media_url

API_PREFIX = "/api/v1"


def video_out(
    video: Video, latest: Analysis | None = None, uploader: str | None = None
) -> VideoOut:
    out = VideoOut.model_validate(video)
    out.uploaded_by_name = uploader
    out.stream_url = (
        sign_media_url(f"{API_PREFIX}/videos/{video.id}/stream") if video.storage_key else None
    )
    out.latest_analysis = AnalysisBrief.model_validate(latest) if latest else None
    return out


def video_outs(session: Session, videos: Sequence[Video]) -> list[VideoOut]:
    """Videos with their latest analysis and uploader name, in two extra queries."""
    ids = [v.id for v in videos]
    user_ids = {v.uploaded_by for v in videos if v.uploaded_by is not None}
    names: dict[int, str] = {}
    if user_ids:
        rows = session.execute(select(User.id, User.name).where(User.id.in_(user_ids)))
        names = {uid: name for uid, name in rows}
    latest: dict[int, Analysis] = {}
    if ids:
        for a in session.scalars(
            select(Analysis).where(Analysis.video_id.in_(ids)).order_by(Analysis.id)
        ):
            latest[a.video_id] = a
    return [video_out(v, latest.get(v.id), names.get(v.uploaded_by)) for v in videos]


def analysis_out(analysis: Analysis) -> AnalysisOut:
    return AnalysisOut(
        **AnalysisBrief.model_validate(analysis).model_dump(),
        engine_version=analysis.engine_version,
        job_id=analysis.job_id,
        result=analysis.result_json,
        evidence=[
            EvidenceOut(
                id=e.id,
                step_key=e.step_key,
                kind=e.kind,
                t_s=e.t_s,
                url=sign_media_url(f"{API_PREFIX}/evidence/{e.id}"),
            )
            for e in analysis.evidence
        ],
    )
