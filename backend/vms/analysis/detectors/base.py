"""Detector protocol and the per-frame signal record detectors fill in."""

from dataclasses import dataclass, field
from typing import Protocol

from vms.analysis.sampling import Frame


@dataclass(frozen=True)
class BarcodeHit:
    value: str
    symbology: str


@dataclass(frozen=True)
class Box:
    role: str  # product | package | label | barcode | tag | seal | hand | tool
    cls: str
    conf: float
    xyxy: tuple[float, float, float, float]


@dataclass
class FrameSignals:
    t_s: float
    valid: bool = False
    blur: float = 0.0
    brightness: float = 0.0
    text_blocks: int | None = None  # None when OCR did not run on this frame
    barcodes: list[BarcodeHit] = field(default_factory=list)
    label: bool = False
    package: bool = False
    tag: bool = False
    product: bool = False
    seal: bool = False
    hand_with_product: bool = False
    tag_close_up: bool = False
    motion_dir: int = 0  # 1 / -1 / 0
    motion_mag: float = 0.0
    boxes: list[Box] = field(default_factory=list)

    def fired(self, kind: str) -> bool:
        """Whether an evidence signal `kind` fired on this frame (used by evidence selection)."""
        if kind == "barcode":
            return bool(self.barcodes)
        if kind == "text":
            return bool(self.text_blocks)
        if kind == "motion":
            return self.motion_dir != 0
        return bool(getattr(self, kind))


EVIDENCE_KINDS = frozenset({"barcode", "text", "motion", "label", "package", "tag", "product"})


class Detector(Protocol):
    """One stage of per-frame analysis. Instances are per-analysis and may keep state."""

    name: str
    available: bool

    def process(self, frame: Frame, signals: FrameSignals) -> None: ...
