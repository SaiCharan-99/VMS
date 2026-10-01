"""The v1 wrapper must keep the old dict shape for app.py-era clients and `/analyze`."""

import pytest

from tests.fixtures.video_factory import make_video
from vms.analysis import analyze_video
from vms.analysis.legacy_analyzer import VMSSOPAnalyzer

V1_KEYS = {
    "total_score",
    "status",
    "decision",
    "confidence",
    "duration_s",
    "detected_barcode",
    "frames_sampled",
    "quality_failures",
    "scores",
    "metrics",
}
V1_METRICS = {
    "pct_label",
    "pct_tag",
    "pct_obj",
    "pct_package",
    "avg_text",
    "direction_changes",
    "estimated_sides",
}


def test_missing_video_raises():
    with pytest.raises(FileNotFoundError):
        VMSSOPAnalyzer().analyze("missing-video.mp4")


@pytest.mark.parametrize("process_type", ["Forward", "Return"])
def test_to_v1_keeps_old_keys(tmp_path, process_type):
    path = make_video(tmp_path / "qr.mp4", qr_text="SOP-RETURN-12345", text="Shipping Label")
    v2 = analyze_video(path, process_type)
    v1 = VMSSOPAnalyzer(process_type=process_type).analyze(path)

    assert v1.keys() == V1_KEYS
    assert v1["metrics"].keys() == V1_METRICS
    assert set(v1["scores"]) == {"shipping_label", "unboxing", "tags", "product"}
    assert v1["scores"]["shipping_label"]["score"] == v2.steps[0].score
    assert v1["scores"]["unboxing"]["notes"] == v2.steps[1].notes
    assert v1["total_score"] == v2.total_score
    assert v1["status"] == v2.status
    assert v1["detected_barcode"] == "SOP-RETURN-12345"
    assert v1["quality_failures"] == v2.video.frames_sampled - v2.quality.frames_ok


def test_wrapper_overrides_settings(tmp_path):
    path = make_video(tmp_path / "plain.mp4", text="SOP SAMPLE")
    strict = VMSSOPAnalyzer(blur_threshold=1e9).analyze(path)
    assert strict["quality_failures"] == strict["frames_sampled"] > 0
    fast = VMSSOPAnalyzer(process_fps=10).analyze(path)
    assert fast["frames_sampled"] > strict["frames_sampled"]


@pytest.mark.models
def test_real_ocr_reads_label_text(tmp_path):
    path = make_video(tmp_path / "ocr.mp4", size=(640, 480), text="SHIPPING LABEL AWB")
    result = VMSSOPAnalyzer().analyze(path)
    assert result["metrics"]["avg_text"] > 0
