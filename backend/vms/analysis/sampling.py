"""Decode a video and yield frames at the analysis rate, downscaled to a fixed width."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

DEFAULT_FPS = 30.0


@dataclass(frozen=True)
class VideoMeta:
    fps: float
    frames_total: int
    width: int
    height: int
    stride: int

    @property
    def duration_s(self) -> float:
        return self.frames_total / self.fps if self.fps else 0.0

    @property
    def sample_interval_s(self) -> float:
        return self.stride / self.fps


@dataclass(frozen=True)
class Frame:
    idx: int  # index in the source video
    t_s: float
    bgr: np.ndarray
    gray: np.ndarray


class VideoSampler:
    """Open with `VideoSampler(path, fps, width)`; iterate for frames, read `.meta` for metadata."""

    def __init__(self, path: Path, process_fps: int, width: int) -> None:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        self._cap = cv2.VideoCapture(str(path))
        if not self._cap.isOpened():
            raise OSError(f"Cannot open video: {path}")
        fps = self._cap.get(cv2.CAP_PROP_FPS) or DEFAULT_FPS
        self.meta = VideoMeta(
            fps=float(fps),
            frames_total=int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT)),
            width=int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
            height=int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            stride=max(1, int(fps / max(process_fps, 1))),
        )
        self._width = width

    def __iter__(self) -> Iterator[Frame]:
        idx = 0
        try:
            while True:
                # grab() skips decoding pixels for frames we don't sample.
                if not self._cap.grab():
                    break
                if idx % self.meta.stride == 0:
                    ok, bgr = self._cap.retrieve()
                    if not ok:
                        break
                    h, w = bgr.shape[:2]
                    if w != self._width:
                        size = (self._width, max(1, round(h * self._width / w)))
                        bgr = cv2.resize(bgr, size, interpolation=cv2.INTER_AREA)
                    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
                    yield Frame(idx=idx, t_s=idx / self.meta.fps, bgr=bgr, gray=gray)
                idx += 1
        finally:
            self._cap.release()
