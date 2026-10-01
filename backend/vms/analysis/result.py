"""AnalysisResult — the versioned result contract (IMPLEMENTATION.md §5)."""

from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "2.0"

Status = Literal["pass", "review", "fail"]
StepStatus = Literal["met", "partial", "missed"]
MetricValue = float | int | bool

DECISIONS: dict[str, str] = {"pass": "Accepted", "review": "Review Required", "fail": "Rejected"}
# v1 consumers (`/analyze`, app.py batch CSV) address steps by these fixed keys, in rubric order.
V1_STEP_KEYS = ("shipping_label", "unboxing", "tags", "product")


class EngineInfo(BaseModel):
    version: str
    detectors: dict[str, bool | str]


class VideoInfo(BaseModel):
    duration_s: float
    fps: float
    frames_total: int
    frames_sampled: int
    width: int
    height: int


class QualitySummary(BaseModel):
    frames_ok: int
    frames_blurry: int
    frames_dark: int
    avg_blur: float
    avg_brightness: float
    ok_ratio: float


class Barcode(BaseModel):
    value: str
    symbology: str
    first_seen_s: float
    frames_seen: int


class CheckResult(BaseModel):
    key: str
    passed: bool
    points: int
    max_points: int
    metric: str
    value: MetricValue | None
    threshold: MetricValue
    note: str | None = None


class Evidence(BaseModel):
    t_s: float
    kind: str
    image: str | None = None  # relative path; None when no evidence dir was given


class StepResult(BaseModel):
    key: str
    title: str
    weight: int
    score: int
    status: StepStatus
    checks: list[CheckResult]
    notes: list[str] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)


class AnalysisResult(BaseModel):
    schema_version: str = SCHEMA_VERSION
    process_type: Literal["Forward", "Return"]
    rubric_id: str
    engine: EngineInfo
    video: VideoInfo
    quality: QualitySummary
    barcodes: list[Barcode]
    metrics: dict[str, MetricValue]
    steps: list[StepResult]
    total_score: int
    confidence: float
    status: Status
    decision: str
    caps_applied: list[str]
    summary: str
    timings_ms: dict[str, int]

    def to_v1(self) -> dict:
        """Legacy v1 dict used by `/analyze` and older clients."""
        m = self.metrics

        def pct(key: str) -> float:
            return round(float(m.get(key, 0.0)) * 100, 1)

        return {
            "total_score": self.total_score,
            "status": self.status,
            "decision": self.decision,
            "confidence": round(self.confidence, 2),
            "duration_s": round(self.video.duration_s, 1),
            "detected_barcode": self.barcodes[0].value if self.barcodes else None,
            "frames_sampled": self.video.frames_sampled,
            "quality_failures": self.video.frames_sampled - self.quality.frames_ok,
            "scores": {
                v1_key: {"score": step.score, "notes": list(step.notes)}
                for v1_key, step in zip(V1_STEP_KEYS, self.steps, strict=True)
            },
            "metrics": {
                "pct_label": pct("label_ratio"),
                "pct_tag": pct("tag_ratio"),
                "pct_obj": pct("product_ratio"),
                "pct_package": pct("package_ratio"),
                "avg_text": round(float(m.get("avg_text_blocks", 0.0)), 1),
                "direction_changes": int(m.get("direction_changes", 0)),
                "estimated_sides": int(m.get("estimated_sides", 0)),
            },
        }
