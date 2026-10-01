"""Lazy singletons for heavy ML models. Nothing here imports torch until first use."""

from vms.analysis.detectors.ocr import get_ocr_reader
from vms.analysis.detectors.yolo import get_yolo

__all__ = ["get_ocr_reader", "get_yolo"]
