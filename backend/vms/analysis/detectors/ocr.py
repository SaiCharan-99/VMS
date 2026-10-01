import importlib.util
import logging
from functools import lru_cache
from typing import Any

import cv2

from vms.analysis.detectors.base import FrameSignals
from vms.analysis.sampling import Frame
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


class OcrDetector:
    """Counts text blocks (EasyOCR text detection only; recognition isn't needed for scoring).

    Runs on every `every_n`-th valid frame, plus on the frame where a label first appears
    (label onset). It must come after the objects detector. The label heuristic fires on most
    real frames, so "every label frame" would mean OCR on every frame, which is too slow on CPU.
    """

    name = "ocr"

    def __init__(self, every_n: int, width: int) -> None:
        self._reader: Any | None = get_ocr_reader()
        self.available = self._reader is not None
        self._every_n = max(1, every_n)
        self._width = width
        self._valid_seen = 0
        self._prev_label = False

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        due = self._valid_seen % self._every_n == 0
        onset = signals.label and not self._prev_label
        self._valid_seen += 1
        self._prev_label = signals.label
        if not self.available or not (due or onset):
            return
        img = frame.bgr
        h, w = img.shape[:2]
        if w > self._width:
            img = cv2.resize(
                img, (self._width, round(h * self._width / w)), interpolation=cv2.INTER_AREA
            )
        horizontal, free = self._reader.detect(img)
        signals.text_blocks = len(horizontal[0]) + len(free[0])
