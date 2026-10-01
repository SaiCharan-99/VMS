import cv2
import numpy as np

from vms.analysis.detectors.base import FrameSignals
from vms.analysis.sampling import Frame


class QualityDetector:
    """Sharpness (Laplacian variance) and brightness gate; runs first on every frame."""

    name = "quality"
    available = True

    def __init__(self, blur_threshold: float, min_brightness: float, max_brightness: float) -> None:
        self.blur_threshold = blur_threshold
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        signals.blur = float(cv2.Laplacian(frame.gray, cv2.CV_64F).var())
        signals.brightness = float(np.mean(frame.gray))
        signals.valid = (
            signals.blur >= self.blur_threshold
            and self.min_brightness <= signals.brightness <= self.max_brightness
        )

    def is_dark(self, signals: FrameSignals) -> bool:
        return signals.brightness < self.min_brightness

    def is_blurry(self, signals: FrameSignals) -> bool:
        return signals.blur < self.blur_threshold
