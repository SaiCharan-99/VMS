"""Re-score cached metrics with any rubric: no CV, so thresholds can be tried in milliseconds."""

from dataclasses import dataclass

from vms.analysis import confidence as confidence_mod
from vms.analysis import rubric as rubric_mod
from vms.analysis.result import MetricValue


@dataclass(frozen=True)
class Scored:
    status: str
    total: int
    confidence: float
    caps: list[str]
    steps: dict[str, str]  # rubric step key -> met | partial | missed


def rescore(rubric: rubric_mod.Rubric, metrics: dict[str, MetricValue]) -> Scored:
    steps = rubric_mod.evaluate(rubric, metrics)
    total = sum(s.score for s in steps)
    conf = confidence_mod.compute(metrics)
    status, _decision, caps = rubric_mod.decide(rubric, total, conf, metrics)
    return Scored(status, total, conf, caps, {s.key: s.status for s in steps})
