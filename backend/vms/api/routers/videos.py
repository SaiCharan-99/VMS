from datetime import date

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from vms.api.deps import PageParams, get_current_user, get_db
from vms.api.schemas import JobOut, Page, ReviewOut, UploadOut, VideoDetail, VideoOut
from vms.api.views import analysis_out, video_out, video_outs
from vms.config import get_settings
from vms.db.models import FinalStatus, ProcessType, User, Video, VideoSource
from vms.services import analyses, jobs
from vms.services import videos as video_svc
from vms.storage import Storage, get_storage

router = APIRouter(prefix="/videos", tags=["videos"])


def _get_video(db: Session, video_id: int) -> Video:
    video = db.get(Video, video_id)
    if video is None or video.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Video not found.")
    return video


@router.post(
    "",
    status_code=201,
    response_model=UploadOut,
    responses={200: {"model": UploadOut, "description": "Duplicate of an existing video"}},
)
def upload_video(
    response: Response,
    file: UploadFile = File(...),
    process_type: ProcessType = Form(...),
    awb: str | None = Form(None),
    order_ref: str | None = Form(None),
    station_id: int | None = Form(None),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> UploadOut:
    """Store the video and queue an analysis job. Returns at once; poll `GET /jobs/{id}`."""
    settings = get_settings()
    try:
        outcome = video_svc.create_from_upload(
            db,
            storage,
            file.file,
            file.filename or "",
            process_type,
            user=user,
            source=VideoSource.web,
            max_bytes=settings.max_upload_mb * 1024 * 1024,
            content_type=file.content_type,
            awb=awb,
            order_ref=order_ref,
            station_id=station_id,
            max_attempts=settings.job_max_attempts,
        )
    except video_svc.UploadRejectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    db.commit()
    if outcome.duplicate:
        response.status_code = 200
    latest = analyses.latest_analysis(db, outcome.video.id)
    return UploadOut(
        video=video_out(outcome.video, latest),
        job=JobOut.model_validate(outcome.job) if outcome.job else None,
        duplicate=outcome.duplicate,
    )


@router.get("", response_model=Page[VideoOut])
def list_videos(
    status: FinalStatus | None = None,
    process_type: ProcessType | None = None,
    awb: str | None = None,
    q: str | None = Query(None, description="Matches filename, AWB, order ref, or any barcode"),
    station_id: int | None = None,
    uploaded_by: int | None = None,
    date_from: date | None = None,
    date_to: date | None = Query(None, description="Inclusive"),
    sort: str = Query("-created_at", enum=list(video_svc.SORTS)),
    paging: PageParams = Depends(),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> Page[VideoOut]:
    filters = video_svc.VideoFilters(
        status, process_type, awb, q, station_id, uploaded_by, date_from, date_to
    )
    stmt = video_svc.list_query(filters, user, sort)
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = db.scalars(stmt.offset(paging.offset).limit(paging.page_size)).all()
    return Page[VideoOut](
        items=video_outs(db, rows), total=total or 0, page=paging.page, page_size=paging.page_size
    )


@router.get("/{video_id}", response_model=VideoDetail)
def get_video(
    video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> VideoDetail:
    """The video, its latest analysis (full result + evidence URLs), reviews, and latest job."""
    video = _get_video(db, video_id)
    latest = analyses.latest_analysis(db, video.id)
    job = jobs.latest_job(db, video.id)
    return VideoDetail(
        video=video_out(video, latest),
        analysis=analysis_out(latest) if latest else None,
        reviews=[ReviewOut.model_validate(r) for r in video.reviews],
        job=JobOut.model_validate(job) if job else None,
    )


@router.get(
    "/{video_id}/stream",
    response_class=FileResponse,
    responses={206: {"description": "Partial content (Range request)"}},
)
def stream_video(
    video_id: int,
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> FileResponse:
    """The video file. Supports HTTP Range for seeking in a `<video>` player."""
    video = _get_video(db, video_id)
    if not video.storage_key or not storage.exists(video.storage_key):
        raise HTTPException(status_code=404, detail="Video file not available.")
    return FileResponse(
        storage.path(video.storage_key),
        media_type=video.content_type or "video/mp4",
        filename=video.original_filename,
        content_disposition_type="inline",
    )


@router.post("/{video_id}/reanalyze", status_code=201, response_model=JobOut)
def reanalyze_video(
    video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> JobOut:
    """Queue a fresh analysis, e.g. after a rubric or model upgrade."""
    video = _get_video(db, video_id)
    if not video.storage_key:
        raise HTTPException(status_code=409, detail="Legacy import has no video file.")
    job = video_svc.reanalyze(db, video, user, get_settings().job_max_attempts)
    db.commit()
    return JobOut.model_validate(job)


@router.delete("/{video_id}", status_code=204)
def delete_video(
    video_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> Response:
    """Soft delete (the file and records are kept for the audit trail)."""
    video_svc.soft_delete(db, _get_video(db, video_id), user)
    db.commit()
    return Response(status_code=204)
