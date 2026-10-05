"""AnalysisResult â€” the versioned result contract (IMPLEMENTATION.md Â§5)."""

from typing import Literal

from pydantic import BaseModel, Field

SCHEMA_VERSION = "2.0"

Status = Literal["pass", "review", "fail"]
StepStatus = Literal["met", "partial", "missed"]
MetricValue = float | int | bool

DECISIONS: dict[str, str] = {"pass": "Accepted", "review": "Review Required", "fail": "Rejected"}


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
    schema_version: Literal["2.0"] = SCHEMA_VERSION
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
