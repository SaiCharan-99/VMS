"""v1 compatibility wrapper: the old constructor and `analyze()` dict, backed by the v2 pipeline."""

from pathlib import Path

from vms.analysis.pipeline import analyze_video
from vms.config import get_settings


class VMSSOPAnalyzer:
    def __init__(
        self,
        blur_threshold: float | None = None,
        process_fps: int | None = None,
        process_type: str = "Return",
    ) -> None:
        overrides = {"blur_threshold": blur_threshold, "process_fps": process_fps}
        self.settings = get_settings().model_copy(
            update={k: v for k, v in overrides.items() if v is not None}
        )
        self.process_type = process_type  # "Return" or "Forward"

    def analyze(self, video_path: str | Path) -> dict:
        return analyze_video(video_path, self.process_type, settings=self.settings).to_v1()
