import logging
from typing import Any

from vms.analysis.detectors import heuristics, model_card
from vms.analysis.detectors.base import Box, FrameSignals
from vms.analysis.detectors.yolo import get_yolo
from vms.analysis.sampling import Frame
from vms.config import Settings

log = logging.getLogger(__name__)


def _area(xyxy: tuple[float, float, float, float]) -> float:
    return max(0.0, xyxy[2] - xyxy[0]) * max(0.0, xyxy[3] - xyxy[1])


def _overlaps(a: tuple[float, ...], b: tuple[float, ...]) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class ObjectsDetector:
    """Label / package / tag / product / seal / hand flags.

    Contour heuristics always run. When YOLO is loaded, boxes whose class is in the class map
    (the model card's, else `settings.yolo_class_map`) set the matching flag. YOLO runs on every
    `yolo_every_n`-th valid frame and whenever the tag heuristic fires; in between, the last
    YOLO flags carry forward.
    """

    name = "objects"
    available = True

    def __init__(self, settings: Settings) -> None:
        self._model: Any | None = get_yolo()
        self._class_map = model_card.class_map(settings)
        self._conf = settings.yolo_conf
        self._every_n = max(1, settings.yolo_every_n)
        self._close_up = settings.tag_close_up_frac
        self._product_fallback = settings.heuristic_product_fallback or self._model is None
        self.backend = settings.yolo_weights.name if self._model is not None else "heuristics"
        self._seen = 0
        self._carried: dict[str, bool] = {}

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        signals.label = heuristics.detect_label_region(frame.gray)
        signals.package = heuristics.detect_package(frame.gray)
        signals.tag = heuristics.detect_small_tag(frame.gray)
        signals.product = self._product_fallback and signals.package
        if self._model is None:
            return
        due = self._seen % self._every_n == 0 or signals.tag
        self._seen += 1
        if due:
            signals.boxes = self._yolo_boxes(frame)
            self._carried = self._flags(signals.boxes, frame)
        signals.product = signals.product or self._carried.get("product", False)
        signals.package = signals.package or self._carried.get("package", False)
        signals.label = signals.label or self._carried.get("label", False)
        signals.tag = signals.tag or self._carried.get("tag", False)
        signals.seal = self._carried.get("seal", False)
        signals.hand_with_product = self._carried.get("hand_with_product", False)
        signals.tag_close_up = self._carried.get("tag_close_up", False)

    def _flags(self, boxes: list[Box], frame: Frame) -> dict[str, bool]:
        by_role: dict[str, list[Box]] = {}
        for b in boxes:
            by_role.setdefault(b.role, []).append(b)
        frame_area = float(frame.bgr.shape[0] * frame.bgr.shape[1])
        flags = {role: True for role in by_role}
        flags["hand_with_product"] = any(
            _overlaps(h.xyxy, p.xyxy)
            for h in by_role.get("hand", [])
            for p in by_role.get("product", [])
        )
        flags["tag_close_up"] = any(
            _area(t.xyxy) >= self._close_up * frame_area for t in by_role.get("tag", [])
        )
        return flags

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
