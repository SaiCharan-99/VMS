import importlib.util
import uuid

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from vms import __version__
from vms.api.deps import get_db
from vms.api.schemas import HealthOut
from vms.config import get_settings

router = APIRouter(tags=["health"])


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


def _storage_state() -> str:
    """Write and remove a probe file: catches a missing or read-only data volume."""
    probe = get_settings().data_dir / f".health-{uuid.uuid4().hex}"
    try:
        probe.parent.mkdir(parents=True, exist_ok=True)
        probe.write_bytes(b"ok")
        probe.unlink()
        return "ok"
    except OSError as exc:
        return f"error: {type(exc).__name__}"


@router.get("/health", response_model=HealthOut, responses={503: {"model": HealthOut}})
def health(response: Response, db: Session = Depends(get_db)) -> HealthOut:
    """DB reachability, a writable data dir, and detector status (configured and installed;
    models are not loaded here). 503 when the DB or storage is down."""
    try:
        db.execute(text("SELECT 1 FROM jobs LIMIT 1"))
        db_state = "ok"
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        db_state = f"error: {type(exc).__name__}"
    storage_state = _storage_state()
    s = get_settings()
    ok = db_state == storage_state == "ok"
    if not ok:
        response.status_code = 503
    return HealthOut(
        status="ok" if ok else "degraded",
        version=__version__,
        db=db_state,
        storage=storage_state,
        detectors={
            "barcode": _installed("pyzbar"),
            "ocr": s.ocr_enabled and _installed("easyocr"),
            "yolo": s.yolo_enabled and _installed("ultralytics"),
        },
    )
