import logging
from collections.abc import Callable

import cv2
import numpy as np

from vms.analysis.detectors.base import BarcodeHit, FrameSignals
from vms.analysis.sampling import Frame

try:
    from pyzbar.pyzbar import decode as pyzbar_decode

    HAS_PYZBAR = True
except ImportError:  # zbar shared library missing
    HAS_PYZBAR = False

log = logging.getLogger(__name__)

# Once a code has been read this often, skip the expensive decode variants.
ENOUGH_SIGHTINGS = 3


def _upscale(gray: np.ndarray) -> np.ndarray:
    return cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)


def _adaptive(gray: np.ndarray) -> np.ndarray:
    return cv2.adaptiveThreshold(
        gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 10
    )


CHEAP_VARIANTS: list[Callable[[np.ndarray], np.ndarray]] = [lambda g: g, cv2.equalizeHist]
EXPENSIVE_VARIANTS: list[Callable[[np.ndarray], np.ndarray]] = [_upscale, _adaptive]


class BarcodeDetector:
    """Decodes every distinct barcode/QR in the video, trying image variants until one reads."""

    name = "barcode"
    available = HAS_PYZBAR

    def __init__(self) -> None:
        self.sightings: dict[str, int] = {}

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        if not self.available:
            return
        variants = CHEAP_VARIANTS
        if not any(n >= ENOUGH_SIGHTINGS for n in self.sightings.values()):
            variants = CHEAP_VARIANTS + EXPENSIVE_VARIANTS
        for variant in variants:
            hits = self._decode(variant(frame.gray))
            if hits:
                signals.barcodes = hits
                for hit in hits:
                    self.sightings[hit.value] = self.sightings.get(hit.value, 0) + 1
                return

    @staticmethod
    def _decode(img: np.ndarray) -> list[BarcodeHit]:
        try:
            results = pyzbar_decode(img)
        except Exception:
            log.debug("pyzbar decode failed", exc_info=True)
            return []
        hits: dict[str, BarcodeHit] = {}
        for r in results:
            value = r.data.decode("utf-8", errors="replace")
            hits.setdefault(value, BarcodeHit(value=value, symbology=r.type))
        return list(hits.values())
