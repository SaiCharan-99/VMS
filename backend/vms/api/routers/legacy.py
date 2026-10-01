"""v1 compatibility shim: synchronous `POST /analyze` and `GET /results` (deprecated in Phase 7)."""

import json
import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.analysis.result import SCHEMA_VERSION, AnalysisResult
from vms.api.deps import get_current_user, get_db
from vms.config import get_settings
from vms.db.models import Analysis, Job, JobStatus, ProcessType, User, Video, VideoSource, utcnow
from vms.services import analyses
from vms.services import videos as video_svc
from vms.storage import Storage, get_storage
from vms.worker import run_job

router = APIRouter(tags=["legacy"])


def _v1(analysis: Analysis) -> dict:
    if analysis.schema_version == SCHEMA_VERSION:
        return AnalysisResult.model_validate(analysis.result_json).to_v1()
    return dict(analysis.result_json)  # legacy import, already v1


@router.post("/analyze", deprecated=True)
def analyze(
    file: UploadFile = File(...),
    process_type: str = Form("Return"),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    user: User = Depends(get_current_user),
) -> dict:
    """Analyze synchronously and return the v1 result. Stored in the new tables like any upload."""
    if process_type not in ProcessType.__members__:
        raise HTTPException(status_code=400, detail="process_type must be 'Return' or 'Forward'.")
    settings = get_settings()
    try:
        outcome = video_svc.create_from_upload(
            db,
            storage,
            file.file,
            file.filename or "",
            ProcessType(process_type),
            user=user,
            source=VideoSource.api,
            max_bytes=settings.max_upload_mb * 1024 * 1024,
            content_type=file.content_type,
            enqueue=False,
        )
    except video_svc.UploadRejectedError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    worker_id = f"api-sync:{uuid.uuid4().hex[:8]}"
    now = utcnow()
    job = Job(
        video_id=outcome.video.id,
        status=JobStatus.running,
        worker_id=worker_id,
        attempts=1,
        max_attempts=1,
        started_at=now,
        heartbeat_at=now,
    )
    db.add(job)
    db.commit()

    if run_job(job.id, worker_id, storage, settings) != "done":
        db.refresh(job)
        raise HTTPException(status_code=400, detail=f"Unable to analyze video: {job.error}")
    analysis = analyses.latest_analysis(db, outcome.video.id)
    result = _v1(analysis)
    result["record_id"] = analysis.id
    return {"status": "ok", "result": result}


@router.get("/results", deprecated=True)
def list_results(limit: int = 20, db: Session = Depends(get_db)) -> dict:
    """Latest analyses in the old `results` row shape (`id` is the analysis id)."""
    rows = db.execute(
        select(Analysis, Video)
        .join(Video, Video.id == Analysis.video_id)
        .order_by(Analysis.id.desc())
        .limit(max(1, min(limit, 100)))
    ).all()
    return {
        "results": [
            {
                "id": a.id,
                "uploaded_at": a.created_at.isoformat(sep=" ", timespec="seconds"),
                "file_name": v.original_filename,
                "process_type": v.process_type.value,
                "status": a.status,
                "decision": a.decision,
                "confidence": a.confidence,
                "total_score": a.total_score,
                "result_json": json.dumps(_v1(a)),
            }
            for a, v in rows
        ]
    }
