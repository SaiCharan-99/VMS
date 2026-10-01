"""Compare model decisions with human labels. The critical number is the false-pass rate."""

import statistics
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from vms.analysis.rubric import Rubric
from vms.evaluation.labels import STATUSES, STEP_COLUMNS, LabelRow
from vms.evaluation.runner import Measured
from vms.evaluation.scoring import Scored, rescore


@dataclass
class VideoOutcome:
    video: str
    process_type: str
    expected: str
    predicted: str
    score: int
    confidence: float
    caps: list[str]
    runtime_ms: int
    cached: bool
    steps: dict[str, str]  # label column -> predicted step status


@dataclass
class EvalReport:
    rubrics: dict[str, str]  # process type -> rubric id
    engine: dict[str, object]
    outcomes: list[VideoOutcome] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


def _rate(num: int, den: int) -> float | None:
    return round(num / den, 4) if den else None


def _step_columns(rubric: Rubric, scored: Scored) -> dict[str, str]:
    return {col: scored.steps[s.key] for col, s in zip(STEP_COLUMNS, rubric.steps, strict=True)}


def summarize(rows: list[LabelRow], outcomes: list[VideoOutcome]) -> dict[str, Any]:
    confusion = {e: {p: 0 for p in STATUSES} for e in STATUSES}
    for o in outcomes:
        confusion[o.expected][o.predicted] += 1
    n = len(outcomes)
    not_pass = [o for o in outcomes if o.expected != "pass"]
    bad = [o for o in outcomes if o.expected == "fail"]
    good = [o for o in outcomes if o.expected == "pass"]
    false_pass = [o for o in not_pass if o.predicted == "pass"]

    steps: dict[str, dict[str, Any]] = {}
    for row, o in zip(rows, outcomes, strict=True):
        for col, human in row.steps.items():
            s = steps.setdefault(col, {"n": 0, "correct": 0, "false_met": 0})
            s["n"] += 1
            s["correct"] += o.steps[col] == human
            s["false_met"] += o.steps[col] == "met" and human != "met"
    for s in steps.values():
        s["accuracy"] = _rate(s["correct"], s["n"])

    runtimes = [o.runtime_ms for o in outcomes]
    return {
        "videos": n,
        "confusion": confusion,
        "false_pass": len(false_pass),
        "false_pass_rate": _rate(len(false_pass), len(not_pass)),
        "false_pass_vs_fail_rate": _rate(sum(o.predicted == "pass" for o in bad), len(bad)),
        "false_pass_videos": [o.video for o in false_pass],
        "false_fail_rate": _rate(sum(o.predicted == "fail" for o in good), len(good)),
        "review_rate": _rate(sum(o.predicted == "review" for o in outcomes), n),
        "status_accuracy": _rate(sum(o.predicted == o.expected for o in outcomes), n),
        "steps": steps,
        "runtime_ms": {
            "mean": round(statistics.fmean(runtimes)) if runtimes else None,
            "max": max(runtimes) if runtimes else None,
        },
    }


def build_report(
    rows: list[LabelRow], measured: list[Measured], rubrics: dict[str, Rubric]
) -> EvalReport:
    outcomes = []
    for row, m in zip(rows, measured, strict=True):
        rubric = rubrics[row.process_type]
        scored = rescore(rubric, m.metrics)
        outcomes.append(
            VideoOutcome(
                video=row.video.name,
                process_type=row.process_type,
                expected=row.expected_status,
                predicted=scored.status,
                score=scored.total,
                confidence=scored.confidence,
                caps=scored.caps,
                runtime_ms=m.runtime_ms,
                cached=m.cached,
                steps=_step_columns(rubric, scored),
            )
        )
    engine = measured[0].engine if measured else {}
    report = EvalReport({pt: r.id for pt, r in rubrics.items()}, engine, outcomes)
    report.summary = summarize(rows, outcomes)
    return report


def _pct(v: float | None) -> str:
    return "n/a" if v is None else f"{v:.1%}"


def render_markdown(report: EvalReport, labels_name: str) -> str:
    s = report.summary
    rt = s["runtime_ms"]
    lines = [
        "# VMS evaluation report",
        "",
        f"- Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"- Labels: `{labels_name}` ({s['videos']} videos)",
        f"- Rubrics: {', '.join(f'`{r}`' for r in report.rubrics.values())}",
        f"- Detectors: `{report.engine.get('detectors')}`",
        "",
        "## Headline",
        "",
        f"- **False-pass rate: {_pct(s['false_pass_rate'])}** "
        f"({s['false_pass']} video(s) a human did not pass were marked pass)",
        f"- Against human `fail` only: {_pct(s['false_pass_vs_fail_rate'])}",
        f"- False-fail rate (compliant video marked fail): {_pct(s['false_fail_rate'])}",
        f"- Review rate: {_pct(s['review_rate'])}",
        f"- Status accuracy: {_pct(s['status_accuracy'])}",
        f"- Runtime per video: mean {rt['mean']} ms, max {rt['max']} ms",
        "",
        "## Confusion matrix (rows = human, columns = model)",
        "",
        "| human / model | pass | review | fail |",
        "|---|---|---|---|",
    ]
    for e in STATUSES:
        c = s["confusion"][e]
        lines.append(f"| {e} | {c['pass']} | {c['review']} | {c['fail']} |")
    if s["steps"]:
        lines += [
            "",
            "## Per-step accuracy",
            "",
            "| step | labelled | accuracy | marked met but not met |",
            "|---|---|---|---|",
        ]
        for col, v in s["steps"].items():
            lines.append(f"| {col} | {v['n']} | {_pct(v['accuracy'])} | {v['false_met']} |")
    if s["false_pass_videos"]:
        lines += ["", "## False passes", ""] + [f"- {v}" for v in s["false_pass_videos"]]
    return "\n".join(lines) + "\n"


def to_json(report: EvalReport) -> dict[str, Any]:
    return {
        "rubrics": report.rubrics,
        "engine": report.engine,
        "summary": report.summary,
        "videos": [o.__dict__ for o in report.outcomes],
    }
