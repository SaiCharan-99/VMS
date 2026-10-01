from unittest.mock import patch

import pytest

from tests.fixtures.video_factory import make_video
from vms.analysis.legacy_analyzer import VMSSOPAnalyzer


def test_missing_video_raises():
    with pytest.raises(FileNotFoundError):
        VMSSOPAnalyzer().analyze("missing-video.mp4")


def test_empty_video_returns_zero_pointers():
    with patch.object(VMSSOPAnalyzer, "_sample_video", return_value=([], 0.0)):
        result = VMSSOPAnalyzer(process_type="Return").analyze("empty-video.mp4")

    assert result["total_score"] == 0
    assert result["confidence"] == 0.0
    assert result["status"] == "fail"
    assert result["frames_sampled"] == 0
    assert result["metrics"]["estimated_sides"] == 0
    assert result["metrics"]["direction_changes"] == 0


def test_analyzer_returns_status_and_confidence_for_valid_video(tmp_path):
    path = make_video(tmp_path / "plain.mp4", text="SOP SAMPLE")
    result = VMSSOPAnalyzer(process_type="Return").analyze(path)
    assert result["status"] in {"pass", "review", "fail"}
    assert "decision" in result
    assert 0.0 <= result["confidence"] <= 1.0


def test_barcode_detection_path_accepts_real_qr_code(tmp_path):
    path = make_video(tmp_path / "qr.mp4", qr_text="SOP-RETURN-12345", text="Shipping Label")
    result = VMSSOPAnalyzer(process_type="Return").analyze(path)
    assert result["detected_barcode"] is not None
    assert "SOP-RETURN-12345" in result["detected_barcode"]


def test_no_barcode_never_passes(tmp_path):
    path = make_video(tmp_path / "nobarcode.mp4", seconds=12, text="LABEL", moving_box=True)
    result = VMSSOPAnalyzer(process_type="Return").analyze(path)
    assert result["detected_barcode"] is None
    assert result["status"] != "pass"


def test_blurry_video_counts_quality_failures(tmp_path):
    path = make_video(tmp_path / "blur.mp4", blur=True)
    result = VMSSOPAnalyzer(process_type="Return").analyze(path)
    assert result["quality_failures"] == result["frames_sampled"] > 0
    assert result["metrics"]["pct_package"] == 0.0
    assert result["status"] == "fail"


def test_motion_metrics_present_for_moving_video(tmp_path):
    path = make_video(tmp_path / "moving.mp4", seconds=3, moving_box=True, text="BOX")
    metrics = VMSSOPAnalyzer().analyze(path)["metrics"]
    assert metrics["direction_changes"] >= 1
    assert 1 <= metrics["estimated_sides"] <= 6


def test_ocr_cadence_uses_sample_index(tmp_path):
    path = make_video(tmp_path / "ocr.mp4", seconds=3, fps=10, text="LABEL TEXT")
    with patch.object(VMSSOPAnalyzer, "_ai_detect_text", return_value=7) as ocr:
        result = VMSSOPAnalyzer(process_fps=10).analyze(path)
    assert result["quality_failures"] == 0
    assert ocr.call_count == len(range(0, result["frames_sampled"], 3))


@pytest.mark.models
def test_real_ocr_reads_label_text(tmp_path):
    path = make_video(tmp_path / "ocr.mp4", size=(640, 480), text="SHIPPING LABEL AWB")
    result = VMSSOPAnalyzer().analyze(path)
    assert result["metrics"]["avg_text"] > 0
