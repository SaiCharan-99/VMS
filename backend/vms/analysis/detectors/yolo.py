import importlib.util
import logging
from functools import lru_cache
from typing import Any

from vms.config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_yolo() -> Any | None:
    """Return a shared YOLO model, or None if disabled or not installed."""
    settings = get_settings()
    if not settings.yolo_enabled or importlib.util.find_spec("ultralytics") is None:
        return None
    from ultralytics import YOLO

    log.info("Loading YOLO weights from %s", settings.yolo_weights)
    return YOLO(str(settings.yolo_weights))
