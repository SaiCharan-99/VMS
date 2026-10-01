"""Pick the best evidence frame per rubric step during the pass and save it as JPEG."""

from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from vms.analysis.detectors.base import FrameSignals
from vms.analysis.result import Evidence
from vms.analysis.rubric import Rubric

JPEG_QUALITY = 85


@dataclass
class _Pick:
    rank: tuple[int, float]
    t_s: float
    kind: str
    bgr: np.ndarray


class EvidenceSelector:
    """Per step, keeps the frame where the top-priority signal fired; ties go to the sharpest."""

    def __init__(self, rubric: Rubric) -> None:
        self._kinds = {s.key: s.evidence for s in rubric.steps}
        self._picks: dict[str, _Pick] = {}

    def offer(self, bgr: np.ndarray, signals: FrameSignals) -> None:
        if not signals.valid:
            return
        for step_key, kinds in self._kinds.items():
            idx = next((i for i, k in enumerate(kinds) if signals.fired(k)), None)
            if idx is None:
                continue
            rank = (-idx, signals.blur)
            current = self._picks.get(step_key)
            if current is None or rank > current.rank:
                self._picks[step_key] = _Pick(rank, signals.t_s, kinds[idx], bgr.copy())

    def save(self, evidence_dir: Path | None, data_dir: Path) -> dict[str, list[Evidence]]:
        """Write JPEGs (when a dir is given). Paths are relative to `data_dir` when the
        evidence dir is inside it, otherwise relative to the evidence dir itself."""
        if evidence_dir is not None:
            evidence_dir.mkdir(parents=True, exist_ok=True)
            try:
                prefix = evidence_dir.resolve().relative_to(data_dir.resolve())
            except ValueError:
                prefix = Path()
        out: dict[str, list[Evidence]] = {}
        for step_key, pick in self._picks.items():
            image = None
            if evidence_dir is not None:
                name = f"{step_key}_0.jpg"
                cv2.imwrite(
                    str(evidence_dir / name), pick.bgr, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY]
                )
                image = (prefix / name).as_posix()
            out[step_key] = [Evidence(t_s=round(pick.t_s, 2), kind=pick.kind, image=image)]
        return out
