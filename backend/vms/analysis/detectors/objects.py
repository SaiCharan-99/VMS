import logging
from typing import Any

from vms.analysis.detectors import heuristics
from vms.analysis.detectors.base import Box, FrameSignals
from vms.analysis.detectors.yolo import get_yolo
from vms.analysis.sampling import Frame
from vms.config import Settings

log = logging.getLogger(__name__)


class ObjectsDetector:
    """Label / package / tag / product flags.

    Contour heuristics always run. When YOLO is loaded, boxes whose class is in
    `settings.yolo_class_map` set `product` / `package` as well.
    """

    name = "objects"
    available = True

    def __init__(self, settings: Settings) -> None:
        self._model: Any | None = get_yolo()
        self._class_map = settings.yolo_class_map
        self._conf = settings.yolo_conf
        self._product_fallback = settings.heuristic_product_fallback or self._model is None
        self.backend = settings.yolo_weights.name if self._model is not None else "heuristics"

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        signals.label = heuristics.detect_label_region(frame.gray)
        signals.package = heuristics.detect_package(frame.gray)
        signals.tag = heuristics.detect_small_tag(frame.gray)
        signals.product = self._product_fallback and signals.package
        if self._model is None:
            return
        signals.boxes = self._yolo_boxes(frame)
        roles = {b.role for b in signals.boxes}
        signals.product = signals.product or "product" in roles
        signals.package = signals.package or "package" in roles

    def _yolo_boxes(self, frame: Frame) -> list[Box]:
        pred = self._model.predict(frame.bgr, conf=self._conf, verbose=False)[0]
        names = pred.names
        boxes = []
        for cls_id, conf, xyxy in zip(
            pred.boxes.cls.tolist(), pred.boxes.conf.tolist(), pred.boxes.xyxy.tolist(), strict=True
        ):
            cls = names[int(cls_id)]
            role = self._class_map.get(cls)
            if role:
                boxes.append(Box(role, cls, round(conf, 3), tuple(round(v, 1) for v in xyxy)))
        return boxes
