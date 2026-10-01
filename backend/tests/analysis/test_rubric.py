from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from vms.analysis.rubric import (
    RUBRICS_DIR,
    Rubric,
    decide,
    evaluate,
    get_rubric,
    load_rubric,
    rubric_for,
)


def _check(key: str, metric: str, op: str, value, points: int, **extra) -> dict:
    return {"key": key, "metric": metric, "op": op, "value": value, "points": points, **extra}


def _rubric_data() -> dict:
    return {
        "id": "test-v1",
        "process_type": "Return",
        "title": "Test",
        "decision": {
            "pass": {"min_score": 85, "min_confidence": 0.7},
            "review": {"min_score": 50, "min_confidence": 0.4},
        },
        "caps": [
            {
                "id": "no_barcode_max_review",
                "when": {"metric": "barcode_found", "op": "==", "value": False},
                "max_status": "review",
            },
            {
                "id": "too_short_fail",
                "when": {"metric": "duration_s", "op": "<", "value": 3},
                "max_status": "fail",
            },
        ],
        "steps": [
            {
                "key": "a",
                "title": "A",
                "checks": [
                    _check("bc", "barcode_found", "==", True, 40),
                    _check(
                        "sides",
                        "estimated_sides",
                        ">=",
                        6,
                        10,
                        fail_note="show sides",
                        partial=[
                            {"op": ">=", "value": 4, "points": 6},
                            {"op": ">=", "value": 2, "points": 3},
                        ],
                    ),
                ],
            },
            {
                "key": "b",
                "title": "B",
                "checks": [
                    _check("ge", "label_ratio", ">=", 0.5, 10),
                    _check("gt", "tag_ratio", ">", 0.5, 10),
                    _check("le", "motion_ratio", "<=", 0.5, 10),
                    _check("lt", "duration_s", "<", 100, 10),
                    _check("ne", "barcode_count", "!=", 0, 10),
                ],
            },
        ],
    }


@pytest.fixture
def rubric() -> Rubric:
    return Rubric.model_validate(_rubric_data())


def test_shipped_rubrics_load_and_differ():
    fwd, ret = rubric_for("Forward"), rubric_for("Return")
    assert (fwd.id, ret.id) == ("forward-v1", "return-v1")
    assert fwd.steps[1].title != ret.steps[1].title
    for r in (fwd, ret):
        assert [s.weight for s in r.steps] == [30, 20, 25, 25]
    six = next(c for c in ret.steps[1].checks if c.key == "six_sides")
    assert six.partial


def test_weights_must_sum_to_100():
    data = _rubric_data()
    data["steps"][1]["checks"].pop()
    with pytest.raises(ValidationError, match="add up to 90"):
        Rubric.model_validate(data)


def test_unknown_metric_raises_at_load(tmp_path: Path):
    data = _rubric_data()
    data["steps"][0]["checks"][0]["metric"] = "no_such_metric"
    path = tmp_path / "bad.yaml"
    path.write_text(yaml.safe_dump(data))
    with pytest.raises(ValidationError, match="no_such_metric"):
        load_rubric(path)


def test_invalid_op_raises():
    data = _rubric_data()
    data["steps"][0]["checks"][0]["op"] = "=~"
    with pytest.raises(ValidationError):
        Rubric.model_validate(data)


def test_partial_points_must_be_below_full():
    data = _rubric_data()
    data["steps"][0]["checks"][1]["partial"][0]["points"] = 10
    with pytest.raises(ValidationError, match="partial points"):
        Rubric.model_validate(data)


METRICS = {
    "barcode_found": True,
    "estimated_sides": 6,
    "label_ratio": 0.5,
    "tag_ratio": 0.6,
    "motion_ratio": 0.5,
    "duration_s": 20.0,
    "barcode_count": 1,
}


def test_each_op_passes(rubric):
    steps = evaluate(rubric, METRICS)
    assert all(c.passed for s in steps for c in s.checks)
    assert [s.status for s in steps] == ["met", "met"]
    assert sum(s.score for s in steps) == 100


@pytest.mark.parametrize(
    ("key", "metric", "value"),
    [
        ("ge", "label_ratio", 0.49),
        ("gt", "tag_ratio", 0.5),
        ("le", "motion_ratio", 0.51),
        ("lt", "duration_s", 100),
        ("ne", "barcode_count", 0),
        ("bc", "barcode_found", False),
    ],
)
def test_each_op_fails(rubric, key, metric, value):
    steps = evaluate(rubric, {**METRICS, metric: value})
    check = next(c for s in steps for c in s.checks if c.key == key)
    assert not check.passed
    assert check.points == 0


@pytest.mark.parametrize(("sides", "points"), [(6, 10), (5, 6), (4, 6), (3, 3), (2, 3), (1, 0)])
def test_partial_tiers(rubric, sides, points):
    step = evaluate(rubric, {**METRICS, "estimated_sides": sides})[0]
    check = step.checks[1]
    assert check.points == points
    assert check.passed is (sides >= 6)
    assert (check.note == "show sides") is (sides < 6)
    assert step.status == ("met" if sides >= 6 else "partial")


def test_missing_metric_fails_check(rubric, caplog):
    metrics = {k: v for k, v in METRICS.items() if k != "estimated_sides"}
    check = evaluate(rubric, metrics)[0].checks[1]
    assert not check.passed
    assert check.points == 0
    assert check.value is None
    assert "estimated_sides" in caplog.text


def test_decision_thresholds(rubric):
    ok = {"barcode_found": True, "duration_s": 20}
    assert decide(rubric, 85, 0.70, ok)[:2] == ("pass", "Accepted")
    assert decide(rubric, 84, 0.99, ok)[:2] == ("review", "Review Required")
    assert decide(rubric, 90, 0.5, ok)[0] == "review"
    assert decide(rubric, 49, 0.9, ok)[:2] == ("fail", "Rejected")


def test_caps_only_downgrade(rubric):
    no_barcode = {"barcode_found": False, "duration_s": 20}
    assert decide(rubric, 100, 1.0, no_barcode) == (
        "review",
        "Review Required",
        ["no_barcode_max_review"],
    )
    # A review cap never lifts a fail, and isn't reported when it changes nothing.
    assert decide(rubric, 10, 1.0, no_barcode) == ("fail", "Rejected", [])
    short = {"barcode_found": True, "duration_s": 1}
    assert decide(rubric, 100, 1.0, short)[2] == ["too_short_fail"]


def test_cap_with_missing_metric_applies(rubric):
    assert decide(rubric, 100, 1.0, {"duration_s": 20})[0] == "review"


@pytest.mark.parametrize("process_type", ["Forward", "Return"])
def test_shipped_caps_block_pass(process_type):
    """Acceptance 3: no barcode or ok_ratio < 0.5 never yields pass, even with a perfect score."""
    r = rubric_for(process_type)
    good = {"barcode_found": True, "quality_ok_ratio": 1.0, "duration_s": 30.0}
    assert decide(r, 100, 1.0, good)[0] == "pass"
    assert decide(r, 100, 1.0, {**good, "barcode_found": False})[0] == "review"
    assert decide(r, 100, 1.0, {**good, "quality_ok_ratio": 0.49})[0] == "review"


def test_yaml_threshold_change_changes_score(tmp_path: Path):
    """Acceptance 2: thresholds live in YAML, not code."""
    metrics = dict.fromkeys(["label_ratio", "tag_ratio", "product_ratio"], 0.0)
    metrics.update(
        package_ratio=0.3,
        avg_text_blocks=0.0,
        barcode_found=False,
        max_label_hold_s=0.0,
        estimated_sides=0,
        direction_changes=0,
        duration_s=20.0,
    )
    before = sum(s.score for s in evaluate(get_rubric("return-v1"), metrics))

    data = yaml.safe_load((RUBRICS_DIR / "return-v1.yaml").read_text())
    for check in data["steps"][1]["checks"]:
        if check["key"] == "package_visible":
            check["value"] = 0.2
    path = tmp_path / "return-v1.yaml"
    path.write_text(yaml.safe_dump(data))
    after = sum(s.score for s in evaluate(load_rubric(path), metrics))
    assert after == before + 6
