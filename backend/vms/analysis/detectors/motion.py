"""Optical-flow motion and the rotation / sides estimate (isolated so Phase 6 can replace it)."""

import cv2
import numpy as np

from vms.analysis.detectors.base import FrameSignals
from vms.analysis.sampling import Frame

FLOW_WIDTH = 320
# Mean flow magnitude (pixels at FLOW_WIDTH) below which a frame is treated as still.
ACTIVE_MAGNITUDE = 0.3
# The v1 analyzer used 5 px at 640 wide.
HIGH_MAGNITUDE = 2.5
# A direction must hold for this many consecutive frames before it counts as a change.
HYSTERESIS_FRAMES = 2


class MotionDetector:
    """Farneback flow between consecutive sampled frames (including low-quality ones)."""

    name = "motion"
    available = True

    def __init__(self) -> None:
        self._prev: np.ndarray | None = None

    def process(self, frame: Frame, signals: FrameSignals) -> None:
        h, w = frame.gray.shape
        small = cv2.resize(frame.gray, (FLOW_WIDTH, max(1, round(h * FLOW_WIDTH / w))))
        prev, self._prev = self._prev, small
        if prev is None or prev.shape != small.shape:
            return
        flow = cv2.calcOpticalFlowFarneback(prev, small, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag = float(np.mean(np.hypot(flow[..., 0], flow[..., 1])))
        half = flow.shape[1] // 2
        left = float(np.mean(flow[:, :half, 0]))
        right = float(np.mean(flow[:, half:, 0]))
        signals.motion_mag = round(mag, 4)
        if mag >= ACTIVE_MAGNITUDE and right != left:
            signals.motion_dir = 1 if right > left else -1


def direction_changes(directions: list[int]) -> int:
    """Count settled direction changes; the first settled direction counts as one (v1 semantics)."""
    changes, settled, candidate, run = 0, 0, 0, 0
    for d in directions:
        if d == 0:
            continue
        run = run + 1 if d == candidate else 1
        candidate = d
        if run >= HYSTERESIS_FRAMES and d != settled:
            settled = d
            changes += 1
    return changes


def estimated_sides(changes: int, motion_ratio: float, n_frames: int) -> int:
    if n_frames == 0:
        return 0
    sides = changes + 1 + (2 if motion_ratio > 0.3 else 0)
    return max(0, min(6, sides))
