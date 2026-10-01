"""Suggest rubric thresholds from labelled, cached metrics. Never applies anything.

Objective, in order: (1) false-pass count (a video a human did not pass, marked pass),
(2) review + false-fail count (manual work and wrong rejections). Caps are never touched, so a
suggestion cannot weaken the review-first rules. A human copies the diff into a new rubric id.
"""

import difflib
from dataclasses import dataclass
from typing import Any

import yaml

from vms.analysis.result import MetricValue
from vms.analysis.rubric import Rubric
from vms.evaluation.scoring import rescore

Cost = tuple[int, int]  # (false passes, review + false fails)
Samples = list[tuple[dict[str, MetricValue], str]]  # (cached metrics, human status)


@dataclass(frozen=True)
class Param:
    label: str
    path: tuple[str | int, ...]  # into the rubric's dict form
    current: float
    candidates: tuple[float, ...]


@dataclass
class Suggestion:
    rubric_id: str
    n: int
    before: Cost
    after: Cost
    changes: list[tuple[str, float, float]]  # label, old, new
    diff: str


def cost(rubric: Rubric, samples: Samples) -> Cost:
    false_pass = soft = 0
    for metrics, expected in samples:
        status = rescore(rubric, metrics).status
        false_pass += status == "pass" and expected != "pass"
        soft += status == "review" or (status == "fail" and expected == "pass")
    return false_pass, soft


def _spread(value: float) -> tuple[float, ...]:
    if isinstance(value, int):
        return tuple(sorted({max(0, round(value * f)) for f in (0.5, 0.75, 1, 1.25, 1.5)}))
    return tuple(sorted({round(value * f, 3) for f in (0.5, 0.75, 1, 1.25, 1.5, 2)}))


def parameters(rubric: Rubric) -> list[Param]:
    """Decision cutoffs plus every numeric (non-boolean) check threshold."""
    d = rubric.decision
    params = [
        Param(
            "decision.pass.min_score",
            ("decision", "pass", "min_score"),
            d.pass_.min_score,
            tuple(range(d.review.min_score + 5, 101, 5)),
        ),
        Param(
            "decision.pass.min_confidence",
            ("decision", "pass", "min_confidence"),
            d.pass_.min_confidence,
            tuple(round(0.5 + 0.05 * i, 2) for i in range(11)),
        ),
        Param(
            "decision.review.min_score",
            ("decision", "review", "min_score"),
            d.review.min_score,
            tuple(range(20, d.pass_.min_score, 5)),
        ),
    ]
    for si, step in enumerate(rubric.steps):
        for ci, check in enumerate(step.checks):
            v = check.value
            if isinstance(v, bool) or not isinstance(v, int | float):
                continue
            path = ("steps", si, "checks", ci, "value")
            params.append(Param(f"{step.key}.{check.key}.value", path, v, _spread(v)))
    return params


def _with(rubric: Rubric, param: Param, value: float) -> Rubric | None:
    data: Any = rubric.model_dump(by_alias=True)
    node = data
    for key in param.path[:-1]:
        node = node[key]
    node[param.path[-1]] = type(param.current)(value)
    try:
        return Rubric.model_validate(data)
    except ValueError:
        return None


def suggest(rubric: Rubric, samples: Samples, *, passes: int = 2) -> Suggestion:
    """Coordinate descent over `parameters()`; a change must strictly lower the cost."""
    best = rubric
    start = best_cost = cost(rubric, samples)
    for _ in range(passes):
        improved = False
        for index in range(len(parameters(best))):
            for value in parameters(best)[index].candidates:
                trial = _with(best, parameters(best)[index], value)
                if trial is None:
                    continue
                c = cost(trial, samples)
                if c < best_cost:
                    best, best_cost, improved = trial, c, True
        if not improved:
            break
    old = {p.label: p.current for p in parameters(rubric)}
    changes = [
        (p.label, old[p.label], p.current) for p in parameters(best) if p.current != old[p.label]
    ]
    new_id = _next_id(rubric.id)
    return Suggestion(new_id, len(samples), start, best_cost, changes, _diff(rubric, best, new_id))


def _next_id(rubric_id: str) -> str:
    base, _, ver = rubric_id.rpartition("-v")
    return f"{base}-v{int(ver) + 1}" if ver.isdigit() else f"{rubric_id}-calibrated"


def _dump(rubric: Rubric) -> str:
    return yaml.safe_dump(rubric.model_dump(by_alias=True), sort_keys=False)


def _diff(old: Rubric, new: Rubric, new_id: str) -> str:
    return "".join(
        difflib.unified_diff(
            _dump(old).splitlines(keepends=True),
            _dump(new).splitlines(keepends=True),
            fromfile=f"{old.id}.yaml",
            tofile=f"{new_id}.yaml (suggested)",
        )
    )
