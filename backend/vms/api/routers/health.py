import importlib.util

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from vms import __version__
from vms.api.deps import get_db
from vms.api.schemas import HealthOut
from vms.config import get_settings

router = APIRouter(tags=["health"])


def _installed(module: str) -> bool:
    return importlib.util.find_spec(module) is not None


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)) -> HealthOut:
    """Liveness plus DB reachability. Detectors are reported as configured and installed;
    models are not loaded here."""
    try:
        db.execute(text("SELECT 1 FROM jobs LIMIT 1"))
        db_state = "ok"
    except Exception as exc:  # noqa: BLE001 - report, don't crash
        db_state = f"error: {type(exc).__name__}"
    s = get_settings()
    return HealthOut(
        status="ok" if db_state == "ok" else "degraded",
        version=__version__,
        db=db_state,
        detectors={
            "barcode": _installed("pyzbar"),
            "ocr": s.ocr_enabled and _installed("easyocr"),
            "yolo": s.yolo_enabled and _installed("ultralytics"),
        },
    )
