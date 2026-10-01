import importlib.util
import logging
from functools import lru_cache
from typing import Any

from vms.config import get_settings

log = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def get_ocr_reader() -> Any | None:
    """Return a shared EasyOCR reader, or None if disabled or not installed."""
    if not get_settings().ocr_enabled or importlib.util.find_spec("easyocr") is None:
        return None
    import easyocr

    log.info("Loading EasyOCR reader (CPU)")
    return easyocr.Reader(["en"], gpu=False)
