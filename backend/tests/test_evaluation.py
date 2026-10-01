"""Phase 6: evaluation harness, calibration, new metrics, model cards, rubric v2, ml/ scripts."""

import csv
import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tests.fixtures.video_factory import make_video
from vms.analysis import analyze_video
from vms.analysis.detectors import model_card
from vms.analysis.detectors.base import BarcodeHit, FrameSignals
from vms.analysis.detectors.objects import ObjectsDetector
from vms.analysis.metrics import METRIC_KEYS, aggregate
from vms.analysis.rubric import get_rubric
from vms.analysis.sampling import Frame
from vms.config import Settings, get_settings
from vms.evaluation import calibrate, report
from vms.evaluation.cli import calibrate_main, evaluate_main
from vms.evaluation.labels import LabelError, LabelRow, read_labels, write_labels
from vms.evaluation.runner import Measured, measure
from vms.evaluation.scoring import rescore
from vms.sop_doc import WHAT_IT_LOOKS_FOR

ML = Path(__file__).resolve().parents[2] / "ml"


def _load_ml(name: str):
    spec = importlib.util.spec_from_file_location(f"ml_{name}", ML / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --- helpers ---------------------------------------------------------------------------------

GOOD = {
    "label_ratio": 1.0, "package_ratio": 1.0, "tag_ratio": 0.5, "product_ratio": 1.0,
    "avg_text_blocks": 9.0, "barcode_found": True, "barcode_count": 1, "duration_s": 40.0,
    "estimated_sides": 6, "direction_changes": 3, "motion_ratio": 0.4, "end_activity_ratio": 0.6,
    "max_label_hold_s": 4.0, "quality_ok_ratio": 1.0, "frames_sampled": 100,
    "seal_visible_ratio": 0.3, "hand_with_product_ratio": 0.4, "tag_close_up_ratio": 0.3,
    "label_and_barcode_ratio": 0.3,
}  # fmt: skip


def _label(name: str, expected: str, steps: dict[str, str] | None = None) -> LabelRow:
    return LabelRow(Path(name), "Return", expected, steps or {})


def _measured(metrics: dict) -> Measured:
    return Measured(Path("x.mp4"), metrics, 1000, {"detectors": {}}, True)


# --- labels ----------------------------------------------------------------------------------


def test_labels_roundtrip_and_relative_paths(tmp_path: Path):
    (tmp_path / "a.mp4").write_bytes(b"x")
    rows = [LabelRow(Path("a.mp4"), "Forward", "review", {"tags": "partial"}, "n")]
    write_labels(tmp_path / "l.csv", rows)
    (got,) = read_labels(tmp_path / "l.csv")
    assert got.video == tmp_path / "a.mp4"  # resolved beside the labels file
    assert got.steps == {"tags": "partial"}
    assert got.expected_status == "review"


@pytest.mark.parametrize(
    "line", ["a.mp4,Return,maybe,,,,,", "a.mp4,Sideways,pass,,,,,", "a.mp4,Return,pass,great,,,,"]
)
def test_labels_reject_bad_values(tmp_path: Path, line: str):
    path = tmp_path / "l.csv"
    path.write_text(
        "video_path,process_type,expected_status,shipping_label,unboxing,tags,product,notes\n"
        + line
    )
    with pytest.raises(LabelError):
        read_labels(path)


def test_example_labels_file_is_valid():
    rows = read_labels(ML / "eval_labels.example.csv")
    assert len(rows) >= 5
    assert {r.expected_status for r in rows} == {"review", "fail"}


# --- report math -----------------------------------------------------------------------------


def test_report_matches_hand_calculation():
    """Humans: pass, review, fail, fail. Model: pass, pass (false pass), fail, review."""
    rubric = get_rubric("return-v1")
    perfect = {**GOOD}
    no_barcode = {**GOOD, "barcode_found": False}  # capped at review
    empty = {**GOOD, "package_ratio": 0.0, "product_ratio": 0.0, "tag_ratio": 0.0,
             "avg_text_blocks": 0.0, "estimated_sides": 0, "direction_changes": 0,
             "max_label_hold_s": 0.0, "barcode_found": False, "label_ratio": 0.0,
             "duration_s": 20.0}  # fmt: skip
    rows = [
        _label("a", "pass", {"tags": "met", "product": "met"}),
        _label("b", "review", {"tags": "missed"}),
        _label("c", "fail", {"tags": "missed"}),
        _label("d", "fail"),
    ]
    rep = report.build_report(
        rows,
        [_measured(perfect), _measured(perfect), _measured(empty), _measured(no_barcode)],
        {"Return": rubric, "Forward": get_rubric("forward-v1")},
    )
    s = rep.summary
    assert [o.predicted for o in rep.outcomes] == ["pass", "pass", "fail", "review"]
    # Not-pass humans: b, c, d (3). Marked pass: b -> 1/3.
    assert s["false_pass"] == 1 and s["false_pass_rate"] == pytest.approx(0.3333, abs=1e-4)
    assert s["false_pass_vs_fail_rate"] == 0.0  # c and d (2 humans-fail): neither passed
    assert s["false_fail_rate"] == 0.0 and s["review_rate"] == 0.25
    assert s["status_accuracy"] == 0.5  # a and c right
    assert s["confusion"]["review"] == {"pass": 1, "review": 0, "fail": 0}
    assert s["confusion"]["fail"] == {"pass": 0, "review": 1, "fail": 1}
    # tags labelled on a (met), b (missed), c (missed): predicted met, met, missed -> 2/3 right;
    # b was marked met but a human said missed.
    assert s["steps"]["tags"] == {"n": 3, "correct": 2, "false_met": 1, "accuracy": 0.6667}
    assert s["false_pass_videos"] == ["b"]
    assert "False-pass rate: 33.3%" in report.render_markdown(rep, "l.csv")


def test_no_not_pass_labels_gives_no_false_pass_rate():
    rep = report.build_report(
        [_label("a", "pass")],
        [_measured(GOOD)],
        {"Return": get_rubric("return-v1"), "Forward": get_rubric("forward-v1")},
    )
    assert rep.summary["false_pass_rate"] is None


# --- cache -----------------------------------------------------------------------------------


def test_measure_caches_and_rescoring_skips_cv(tmp_path: Path):
    video = make_video(tmp_path / "v.mp4", qr_text="AWB1", seconds=3)
    row = LabelRow(video, "Return", "review")
    cache = tmp_path / "cache"
    first = measure(row, cache)
    second = measure(row, cache)
    assert first is not None and not first.cached
    assert second is not None and second.cached and second.metrics == first.metrics
    assert measure(row, cache, use_cache=False).cached is False
    # Re-scoring with another rubric needs only the cached metrics.
    assert set(first.metrics) == METRIC_KEYS
    assert rescore(get_rubric("return-v2"), second.metrics).status in {"review", "fail"}


def test_cache_misses_when_engine_settings_change(tmp_path: Path, monkeypatch):
    video = make_video(tmp_path / "v.mp4", seconds=2)
    row = LabelRow(video, "Return", "fail")
    measure(row, tmp_path / "c")
    monkeypatch.setenv("VMS_PROCESS_FPS", "2")
    get_settings.cache_clear()
    assert measure(row, tmp_path / "c", cache_only=True) is None


# --- CLI end to end (acceptance 1) ------------------------------------------------------------


def _synthetic_labels(tmp_path: Path) -> Path:
    qr = make_video(tmp_path / "qr.mp4", qr_text="AWB9", seconds=3)
    dark = make_video(tmp_path / "dark.mp4", qr_text="AWB8", dark=True, seconds=3)
    path = tmp_path / "labels.csv"
    write_labels(path, [LabelRow(qr, "Return", "review"), LabelRow(dark, "Forward", "fail")])
    return path


def test_evaluate_cli_end_to_end_then_from_cache(tmp_path: Path, capsys):
    labels = _synthetic_labels(tmp_path)
    out = tmp_path / "out"
    assert evaluate_main(["--labels", str(labels), "--out-dir", str(out)]) == 0
    (md,) = out.glob("report_*.md")
    data = json.loads(next(out.glob("report_*.json")).read_text())
    assert data["summary"]["videos"] == 2
    assert data["summary"]["false_pass"] == 0
    assert "False-pass rate" in md.read_text()

    capsys.readouterr()
    assert (
        evaluate_main(
            [
                "--labels",
                str(labels),
                "--out-dir",
                str(out),
                "--rubric",
                "return-v2",
                "--from-cache",
            ]
        )
        == 0
    )
    assert "cached" in capsys.readouterr().err
    assert len(list(out.glob("report_*.json"))) >= 1


def test_from_cache_skips_uncached_videos(tmp_path: Path):
    labels = _synthetic_labels(tmp_path)
    assert (
        evaluate_main(["--labels", str(labels), "--out-dir", str(tmp_path / "o"), "--from-cache"])
        == 1
    )


def test_evaluate_cli_reports_missing_videos(tmp_path: Path):
    labels = tmp_path / "l.csv"
    write_labels(labels, [_label("nope.mp4", "pass")])
    assert evaluate_main(["--labels", str(labels), "--out-dir", str(tmp_path / "o")]) == 1


def test_ml_scripts_are_thin_wrappers():
    for name in ("evaluate", "calibrate"):
        assert (ML / f"{name}.py").read_text().count("vms.evaluation.cli") == 1


# --- calibration -----------------------------------------------------------------------------


def test_calibration_removes_false_pass_and_never_touches_caps():
    rubric = get_rubric("return-v1")
    weak = {**GOOD, "tag_ratio": 0.0, "avg_text_blocks": 0.0, "product_ratio": 0.5,
            "estimated_sides": 2, "direction_changes": 0}  # fmt: skip
    base = rescore(rubric, weak)
    assert base.status == "review"  # 54 or so: below pass
    near_pass = {**GOOD, "estimated_sides": 5, "max_label_hold_s": 1.0}
    assert rescore(rubric, near_pass).status == "pass"
    samples = [(GOOD, "pass"), (near_pass, "fail"), (weak, "fail")]
    assert calibrate.cost(rubric, samples) == (1, 1)

    s = calibrate.suggest(rubric, samples)
    assert s.before == (1, 1) and s.after[0] == 0
    assert s.rubric_id == "return-v2"
    assert "(suggested)" in s.diff and s.changes
    # Caps are not tunable parameters.
    assert not any("cap" in label for label, _, _ in s.changes)
    new = get_rubric("return-v1")  # the shipped rubric object is unchanged
    assert new.decision.pass_.min_score == 85


def test_calibration_prefers_fewer_false_passes_over_fewer_reviews():
    rubric = get_rubric("return-v1")
    review_only = {**GOOD, "estimated_sides": 5, "max_label_hold_s": 1.0}
    # Human says fail; lowering reviews by passing it would be cheaper in work but is a false pass.
    s = calibrate.suggest(rubric, [(review_only, "fail")])
    assert s.after[0] == 0


def test_calibrate_cli_writes_a_diff_and_changes_nothing(tmp_path: Path):
    labels = _synthetic_labels(tmp_path)
    out = tmp_path / "out"
    evaluate_main(["--labels", str(labels), "--out-dir", str(out)])
    before = (Path(__file__).parents[1] / "vms/analysis/rubrics/return-v1.yaml").read_text()
    assert (
        calibrate_main(["--labels", str(labels), "--out-dir", str(out), "--min-videos", "1"]) == 0
    )
    after = (Path(__file__).parents[1] / "vms/analysis/rubrics/return-v1.yaml").read_text()
    assert before == after


# --- new metrics -----------------------------------------------------------------------------


def test_new_metrics_on_hand_built_signals():
    signals = [
        FrameSignals(0, valid=True, seal=True, hand_with_product=True, label=True,
                     barcodes=[BarcodeHit("A", "QRCODE")]),
        FrameSignals(1, valid=True, tag_close_up=True, label=True),
        FrameSignals(2, valid=True),
        FrameSignals(3, valid=True),
        FrameSignals(4, valid=False, seal=True, tag_close_up=True),  # ignored: not valid
    ]  # fmt: skip
    m = aggregate(signals, 5.0, 1.0)
    assert m["seal_visible_ratio"] == 0.25
    assert m["hand_with_product_ratio"] == 0.25
    assert m["tag_close_up_ratio"] == 0.25
    assert m["label_and_barcode_ratio"] == 0.25
    assert m.keys() == METRIC_KEYS


# --- model card + detector -------------------------------------------------------------------


def _card(path: Path, class_map: dict[str, str]) -> None:
    path.write_text(json.dumps({"class_map": class_map}), encoding="utf-8")


def test_class_map_comes_from_model_card_beside_weights(tmp_path: Path):
    weights = tmp_path / "vms-det-1.pt"
    _card(tmp_path / "vms-det-1.model_card.json", {"seal_tape": "seal"})
    s = Settings(yolo_weights=weights)
    assert model_card.class_map(s) == {"seal_tape": "seal"}
    assert model_card.class_map(Settings(yolo_weights=tmp_path / "other.pt")) == s.yolo_class_map


def test_bad_model_card_falls_back(tmp_path: Path):
    weights = tmp_path / "w.pt"
    (tmp_path / "w.model_card.json").write_text("{not json")
    assert model_card.class_map(Settings(yolo_weights=weights)) == Settings().yolo_class_map
    _card(tmp_path / "w.model_card.json", {"x": "spaceship"})
    assert model_card.class_map(Settings(yolo_weights=weights)) == Settings().yolo_class_map


class _FakeYolo:
    """Returns the queued detections, one list per predict() call."""

    def __init__(self, detections: list[list[tuple[str, float, float, float, float]]]) -> None:
        self.names = {0: "seal_tape", 1: "hand", 2: "product", 3: "brand_tag", 4: "cat"}
        self._ids = {v: k for k, v in self.names.items()}
        self.queue = list(detections)
        self.calls = 0

    def predict(self, bgr, conf, verbose):
        self.calls += 1
        dets = self.queue.pop(0) if self.queue else []
        boxes = SimpleNamespace(
            cls=SimpleNamespace(tolist=lambda: [self._ids[d[0]] for d in dets]),
            conf=SimpleNamespace(tolist=lambda: [0.9] * len(dets)),
            xyxy=SimpleNamespace(tolist=lambda: [list(d[1:]) for d in dets]),
        )
        return [SimpleNamespace(names=self.names, boxes=boxes)]


def _frame(w: int = 100, h: int = 100) -> Frame:
    bgr = np.full((h, w, 3), 128, dtype=np.uint8)
    return Frame(idx=0, t_s=0.0, bgr=bgr, gray=cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY))


def _detector(monkeypatch, tmp_path: Path, fake: _FakeYolo, **kw) -> ObjectsDetector:
    _card(
        tmp_path / "w.model_card.json",
        {"seal_tape": "seal", "hand": "hand", "product": "product", "brand_tag": "tag"},
    )
    monkeypatch.setattr("vms.analysis.detectors.objects.get_yolo", lambda: fake)
    return ObjectsDetector(Settings(yolo_weights=tmp_path / "w.pt", **kw))


def test_objects_detector_maps_roles_from_card(monkeypatch, tmp_path: Path):
    fake = _FakeYolo([[
        ("seal_tape", 0, 0, 10, 10), ("hand", 20, 20, 60, 60), ("product", 40, 40, 90, 90),
        ("brand_tag", 0, 50, 40, 90), ("cat", 0, 0, 5, 5),
    ]])  # fmt: skip
    det = _detector(monkeypatch, tmp_path, fake)
    sig = FrameSignals(0, valid=True)
    det.process(_frame(), sig)
    assert {b.role for b in sig.boxes} == {"seal", "hand", "product", "tag"}  # "cat" has no role
    assert sig.seal and sig.product and sig.tag
    assert sig.hand_with_product  # hand (20..60) overlaps product (40..90)
    assert sig.tag_close_up  # 40 x 40 box = 16 % of the frame >= 4 %


def test_hand_apart_from_product_and_small_tag(monkeypatch, tmp_path: Path):
    fake = _FakeYolo(
        [[("hand", 0, 0, 10, 10), ("product", 50, 50, 90, 90), ("brand_tag", 0, 0, 10, 10)]]
    )
    det = _detector(monkeypatch, tmp_path, fake)
    sig = FrameSignals(0, valid=True)
    det.process(_frame(), sig)
    assert not sig.hand_with_product
    assert not sig.tag_close_up  # 1 % of the frame < 4 %


def test_yolo_runs_every_k_frames_and_carries_flags(monkeypatch, tmp_path: Path):
    fake = _FakeYolo([[("seal_tape", 0, 0, 10, 10)]])
    det = _detector(monkeypatch, tmp_path, fake, yolo_every_n=3)
    seen = []
    for _ in range(4):
        sig = FrameSignals(0, valid=True)
        det.process(_frame(), sig)
        seen.append(sig.seal)
    assert fake.calls == 2  # frames 0 and 3
    assert seen == [True, True, True, False]  # carried until the next run found nothing


# --- rubric v2 + config-only switching (acceptance 3) ----------------------------------------


@pytest.mark.parametrize("rid", ["forward-v2", "return-v2"])
def test_v2_rubrics_load_and_keep_the_v1_caps(rid: str):
    v2, v1 = get_rubric(rid), get_rubric(rid.replace("v2", "v1"))
    assert [s.weight for s in v2.steps] == [30, 20, 25, 25]
    assert [s.key for s in v2.steps] == [s.key for s in v1.steps]
    assert v2.caps == v1.caps  # review-first rules are not weakened
    assert {"seal_visible", "tag_close_up", "hand_on_product", "label_with_barcode"} <= {
        c.key for s in v2.steps for c in s.checks
    }
    for step in v2.steps:
        for c in step.checks:
            assert c.key in WHAT_IT_LOOKS_FOR, f"add plain wording for {c.key}"


def test_v2_without_custom_model_cannot_pass():
    """No seal/hand/tag-close-up signal (COCO or heuristics only) -> v2 never gives a pass."""
    heuristics_only = {**GOOD, "seal_visible_ratio": 0.0, "hand_with_product_ratio": 0.0,
                       "tag_close_up_ratio": 0.0, "label_and_barcode_ratio": 0.0}  # fmt: skip
    assert rescore(get_rubric("return-v1"), heuristics_only).status == "pass"
    assert rescore(get_rubric("return-v2"), heuristics_only).status != "pass"
    assert rescore(get_rubric("return-v2"), GOOD).status == "pass"


def test_rubric_is_switched_by_settings_only(tmp_path: Path, monkeypatch):
    video = make_video(tmp_path / "v.mp4", qr_text="AWB1", seconds=3)
    assert analyze_video(video, "Forward").rubric_id == "forward-v1"
    monkeypatch.setenv("VMS_RUBRIC_FORWARD", "forward-v2")
    get_settings.cache_clear()
    assert analyze_video(video, "Forward").rubric_id == "forward-v2"
    assert analyze_video(video, "Return").rubric_id == "return-v1"  # per process type
    assert analyze_video(video, "Return", rubric_id="return-v2").rubric_id == "return-v2"


# --- export from reviews ---------------------------------------------------------------------


def test_export_eval_from_reviews(tmp_path: Path, make_user):
    from vms.db import session_scope
    from vms.db.models import Analysis, ProcessType, Review, ReviewStatus, Role, Video, VideoSource
    from vms.evaluation.export import export_reviewed
    from vms.storage import get_storage

    reviewer = make_user(Role.reviewer)
    storage = get_storage()
    with session_scope() as s:
        for name, decisions in (("a", ["fail", "pass"]), ("b", ["fail"]), ("gone", ["pass"])):
            v = Video(
                original_filename=f"{name}.mp4",
                storage_key=f"videos/{name}.mp4",
                process_type=ProcessType.Return,
                source=VideoSource.web,
            )
            s.add(v)
            s.flush()
            if name != "gone":
                p = storage.path(v.storage_key)
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"x")
            a = Analysis(
                video_id=v.id, schema_version="2.0", engine_version="t", rubric_id="return-v1",
                total_score=50, confidence=0.5, status="review", decision="Review", result_json={},
            )  # fmt: skip
            s.add(a)
            s.flush()
            for d in decisions:
                s.add(
                    Review(
                        analysis_id=a.id, video_id=v.id, reviewer_id=reviewer.id,
                        final_status=ReviewStatus(d), reason_code="other", comment="c",
                    )
                )  # fmt: skip
        s.flush()
        rows, skipped = export_reviewed(s)
    assert skipped == 1
    by_name = {r.video.name: r for r in rows}
    assert by_name["a.mp4"].expected_status == "pass"  # latest review wins
    assert by_name["b.mp4"].expected_status == "fail"
    assert by_name["a.mp4"].process_type == "Return"

    out = tmp_path / "labels.csv"
    write_labels(out, rows)
    assert len(list(csv.DictReader(out.open()))) == 2


# --- ml/ scripts -----------------------------------------------------------------------------


def _static_video_with_scene_change(path: Path) -> Path:
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), 10, (160, 120))
    rng = np.random.default_rng(1)
    still = np.full((120, 160, 3), 200, np.uint8)
    cv2.rectangle(still, (10, 10), (80, 60), (30, 30, 30), -1)
    other = rng.integers(0, 255, (120, 160, 3), dtype=np.uint8)
    for i in range(40):
        writer.write(still if i < 20 else other)
    writer.release()
    return path


def test_extract_frames_dedupes_and_caps(tmp_path: Path):
    ef = _load_ml("extract_frames")
    video = _static_video_with_scene_change(tmp_path / "clip.mp4")
    out = tmp_path / "frames"
    # Frames at 0,1,2,3 s: the first two seconds are one image, then a different scene.
    assert ef.extract_video(video, out / "d", every_seconds=0.5) == 2
    assert len(list((out / "d").glob("*.jpg"))) == 2
    assert ef.extract_video(video, out / "nodedupe", every_seconds=0.5, dedupe_distance=-1) == 8
    assert (
        ef.extract_video(video, out / "cap", every_seconds=0.5, max_per_video=3, dedupe_distance=-1)
        == 3
    )
    assert ef.extract_frames(tmp_path, tmp_path / "all", every_seconds=1.0) == 2
    assert (tmp_path / "all" / "clip").is_dir()


def test_train_model_card_and_dataset_hash(tmp_path: Path):
    train = _load_ml("train")
    data = tmp_path / "yolo"
    (data / "images" / "train").mkdir(parents=True)
    (data / "labels" / "train").mkdir(parents=True)
    (data / "images" / "train" / "a.jpg").write_bytes(b"1234")
    (data / "labels" / "train" / "a.txt").write_text("0 0.5 0.5 0.2 0.2")
    cfg = tmp_path / "data.yaml"
    cfg.write_text(
        (ML / "data.yaml").read_text().replace("path: data/yolo", f"path: {data.as_posix()}")
    )
    h1 = train.dataset_hash(cfg)
    assert train.dataset_hash(cfg) == h1
    (data / "labels" / "train" / "b.txt").write_text("1 0.5 0.5 0.1 0.1")
    assert train.dataset_hash(cfg) != h1

    names = {0: "shipping_label", 1: "seal_tape", 2: "mystery"}
    card = train.build_card(
        names=names,
        metrics={"map50": 0.5},
        data_hash=h1,
        base_model="yolov8s.pt",
        epochs=1,
        imgsz=640,
    )
    assert card["class_map"] == {"shipping_label": "label", "seal_tape": "seal"}
    assert card["classes"] == ["shipping_label", "seal_tape", "mystery"]
    assert card["data_hash"] == h1
    with pytest.raises(ValueError):
        train.build_card(
            names=names, metrics={}, data_hash=h1, base_model="m", epochs=1, imgsz=1,
            class_roles={"mystery": "spaceship"},
        )  # fmt: skip


def test_data_yaml_classes_match_default_class_roles():
    import yaml

    names = yaml.safe_load((ML / "data.yaml").read_text())["names"]
    assert set(names.values()) == set(model_card.DEFAULT_CLASS_ROLES)
