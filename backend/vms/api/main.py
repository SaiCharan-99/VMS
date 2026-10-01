import logging
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile

from vms import __version__
from vms.analysis.legacy_analyzer import VMSSOPAnalyzer
from vms.config import get_settings
from vms.legacy_store import AuditStore
from vms.logging import configure_logging

configure_logging()
log = logging.getLogger(__name__)

app = FastAPI(title="VMS SOP Analyzer API", version=__version__)

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".wmv"}
CHUNK_BYTES = 1024 * 1024


@lru_cache
def get_store() -> AuditStore:
    return AuditStore()


@app.get("/health")
def health_check() -> dict:
    return {"status": "ok", "service": "vms-sop-analyzer", "version": __version__}


@app.post("/analyze")
async def analyze_video(
    file: UploadFile = File(...),
    process_type: str = Form("Return"),
    store: AuditStore = Depends(get_store),
) -> dict:
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected.")

    extension = Path(file.filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {extension}. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    if process_type not in {"Return", "Forward"}:
        raise HTTPException(status_code=400, detail="process_type must be 'Return' or 'Forward'.")

    max_bytes = get_settings().max_upload_mb * 1024 * 1024
    with tempfile.TemporaryDirectory() as tmp_dir:
        temp_path = Path(tmp_dir) / f"upload{extension}"
        written = 0
        with temp_path.open("wb") as out:
            while chunk := await file.read(CHUNK_BYTES):
                written += len(chunk)
                if written > max_bytes:
                    raise HTTPException(status_code=413, detail="File too large.")
                out.write(chunk)

        try:
            result = VMSSOPAnalyzer(process_type=process_type).analyze(temp_path)
        except Exception as exc:
            log.warning("Analysis failed for %s: %s", file.filename, exc)
            raise HTTPException(status_code=400, detail=f"Unable to analyze video: {exc}") from exc

    result["record_id"] = store.save(file.filename, process_type, result)
    return {"status": "ok", "result": result}


@app.get("/results")
def list_results(limit: int = 20, store: AuditStore = Depends(get_store)) -> dict:
    return {"results": store.list_recent(limit=max(1, min(limit, 100)))}
