"""YAML rubrics: load + validate, evaluate metrics into step scores, decide status with caps."""

import logging
import operator
from functools import cache
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field, model_validator

from vms.analysis.detectors.base import EVIDENCE_KINDS
from vms.analysis.metrics import METRIC_KEYS
from vms.analysis.result import DECISIONS, CheckResult, MetricValue, Status, StepResult
from vms.config import Settings, get_settings

log = logging.getLogger(__name__)

RUBRICS_DIR = Path(__file__).parent / "rubrics"
TOTAL_POINTS = 100

Op = Literal[">=", ">", "<=", "<", "==", "!="]
OPS = {">=": operator.ge, ">": operator.gt, "<=": operator.le, "<": operator.lt,
       "==": operator.eq, "!=": operator.ne}  # fmt: skip
STATUS_RANK: dict[Status, int] = {"fail": 0, "review": 1, "pass": 2}


class _Strict(BaseModel):
    model_config = {"extra": "forbid"}


class Condition(_Strict):
    metric: str
    op: Op
    value: MetricValue

    def test(self, metrics: dict[str, MetricValue]) -> bool | None:
        """True/False, or None when the metric is missing."""
        if self.metric not in metrics:
            return None
        return bool(OPS[self.op](metrics[self.metric], self.value))


class Tier(_Strict):
    op: Op
    value: MetricValue
    points: int = Field(gt=0)


class Check(Condition):
    key: str
    points: int = Field(gt=0)
    fail_note: str | None = None
    partial: list[Tier] = Field(default_factory=list)

    @model_validator(mode="after")
    def _tiers_below_full(self) -> "Check":
        if any(t.points >= self.points for t in self.partial):
            raise ValueError(f"check {self.key}: partial points must be below {self.points}")
        return self


class Step(_Strict):
    key: str
    title: str
    description: str = ""
    evidence: list[str] = Field(default_factory=list)  # signal kinds, in priority order
    checks: list[Check] = Field(min_length=1)

    @property
    def weight(self) -> int:
        return sum(c.points for c in self.checks)


class Threshold(_Strict):
    min_score: int
    min_confidence: float


class DecisionRule(_Strict):
    pass_: Threshold = Field(alias="pass")
    review: Threshold


class Cap(_Strict):
    id: str
    when: Condition
    max_status: Status


class Rubric(_Strict):
    id: str
    process_type: Literal["Forward", "Return"]
    title: str
    decision: DecisionRule
    caps: list[Cap] = Field(default_factory=list)
    steps: list[Step] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate(self) -> "Rubric":
        total = sum(s.weight for s in self.steps)
        if total != TOTAL_POINTS:
            raise ValueError(f"step weights add up to {total}, expected {TOTAL_POINTS}")
        metrics = [c.metric for s in self.steps for c in s.checks] + [
            c.when.metric for c in self.caps
        ]
        unknown = sorted(set(metrics) - METRIC_KEYS)
        if unknown:
            raise ValueError(f"unknown metrics: {unknown}")
        kinds = {k for s in self.steps for k in s.evidence} - EVIDENCE_KINDS
        if kinds:
            raise ValueError(f"unknown evidence kinds: {sorted(kinds)}")
        return self


def load_rubric(path: Path) -> Rubric:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return Rubric.model_validate(data)


@cache
def get_rubric(rubric_id: str) -> Rubric:
    return load_rubric(RUBRICS_DIR / f"{rubric_id}.yaml")


def active_rubric_ids(settings: Settings | None = None) -> dict[str, str]:
    """Process type -> active rubric id (`VMS_RUBRIC_FORWARD` / `VMS_RUBRIC_RETURN`)."""
    settings = settings or get_settings()
    return {"Forward": settings.rubric_forward, "Return": settings.rubric_return}


def rubric_for(process_type: str, settings: Settings | None = None) -> Rubric:
    return get_rubric(active_rubric_ids(settings)[process_type])


def _evaluate_check(check: Check, metrics: dict[str, MetricValue]) -> CheckResult:
    value = metrics.get(check.metric)
    passed = check.test(metrics)
    if passed is None:
        log.warning("Rubric metric %r missing; check %s fails", check.metric, check.key)
    points = check.points if passed else 0
    if passed is False:
        tier = next((t for t in check.partial if OPS[t.op](value, t.value)), None)
        points = tier.points if tier else 0
    return CheckResult(
        key=check.key,
        passed=bool(passed),
        points=points,
        max_points=check.points,
        metric=check.metric,
        value=value,
        threshold=check.value,
        note=None if passed else check.fail_note,
    )


def evaluate(rubric: Rubric, metrics: dict[str, MetricValue]) -> list[StepResult]:
    steps = []
    for step in rubric.steps:
        checks = [_evaluate_check(c, metrics) for c in step.checks]
        score = sum(c.points for c in checks)
        status = "met" if score == step.weight else "partial" if score > 0 else "missed"
        steps.append(
            StepResult(
                key=step.key,
                title=step.title,
                weight=step.weight,
                score=score,
                status=status,
                checks=checks,
                notes=[c.note for c in checks if c.note],
            )
        )
    return steps


def decide(
    rubric: Rubric, total_score: int, confidence: float, metrics: dict[str, MetricValue]
) -> tuple[Status, str, list[str]]:
    """Score/confidence thresholds, then caps. Caps only ever lower the status.

    A cap whose metric is missing applies (review-first: unknown never helps a video pass).
    """
    rule = rubric.decision
    status: Status = "fail"
    if total_score >= rule.pass_.min_score and confidence >= rule.pass_.min_confidence:
        status = "pass"
    elif total_score >= rule.review.min_score and confidence >= rule.review.min_confidence:
        status = "review"

    applied = []
    for cap in rubric.caps:
        if (
            cap.when.test(metrics) is not False
            and STATUS_RANK[cap.max_status] < STATUS_RANK[status]
        ):
            status = cap.max_status
            applied.append(cap.id)
    return status, DECISIONS[status], applied
