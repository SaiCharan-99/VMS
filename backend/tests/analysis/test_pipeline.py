from pathlib import Path

import pytest

from tests.fixtures.video_factory import make_video
from vms.analysis import analyze_video
from vms.analysis.detectors import ocr as ocr_mod
from vms.analysis.result import AnalysisResult
from vms.analysis.sampling import VideoSampler


@pytest.fixture(scope="module")
def videos(tmp_path_factory) -> dict[str, Path]:
    d = tmp_path_factory.mktemp("videos")
    return {
        "qr": make_video(d / "qr.mp4", seconds=4, qr_text="AWB-1234", text="LABEL"),
        "dark": make_video(d / "dark.mp4", dark=True, qr_text="AWB-DARK"),
        "blur": make_video(d / "blur.mp4", blur=True),
        "short": make_video(d / "short.mp4", seconds=0.5),
        "moving": make_video(d / "moving.mp4", seconds=3, moving_box=True, text="BOX"),
    }


def test_missing_video_raises():
    with pytest.raises(FileNotFoundError):
        analyze_video("missing.mp4", "Return")


def test_qr_video_reads_barcode(videos):
    r = analyze_video(videos["qr"], "Return")
    AnalysisResult.model_validate(r.model_dump())  # schema round-trip
    assert r.schema_version == "2.0"
    assert r.metrics["barcode_found"] is True
    [code] = r.barcodes
    assert code.value == "AWB-1234"
    assert code.symbology == "QRCODE"
    assert code.first_seen_s == 0.0
    assert code.frames_seen == r.video.frames_sampled
    assert r.steps[0].checks[2].passed  # barcode_read


@pytest.mark.parametrize("name", ["dark", "blur"])
def test_poor_quality_never_passes(videos, name):
    r = analyze_video(videos[name], "Return")
    assert r.quality.ok_ratio < 0.5
    assert r.status in {"review", "fail"}
    if name == "dark":
        assert r.quality.frames_dark == r.video.frames_sampled
    else:
        assert r.quality.frames_blurry == r.video.frames_sampled


def test_very_short_video_fails_with_zero(videos):
    r = analyze_video(videos["short"], "Return")
    assert r.status == "fail"
    assert r.total_score == 0


def test_empty_video_fails_with_zero(videos, monkeypatch):
    monkeypatch.setattr(VideoSampler, "__iter__", lambda self: iter(()))
    r = analyze_video(videos["qr"], "Forward")
    assert (r.status, r.total_score, r.confidence) == ("fail", 0, 0.0)
    assert r.video.frames_sampled == 0
    assert r.metrics["estimated_sides"] == 0


def test_moving_box_has_direction_changes(videos):
    r = analyze_video(videos["moving"], "Return")
    assert r.metrics["direction_changes"] > 0
    assert 1 <= r.metrics["estimated_sides"] <= 6


def test_forward_and_return_use_different_rubrics(videos):
    fwd = analyze_video(videos["qr"], "Forward")
    ret = analyze_video(videos["qr"], "Return")
    assert (fwd.rubric_id, ret.rubric_id) == ("forward-v1", "return-v1")
    assert fwd.steps[1].title == "Packing & Sealing"
    assert ret.steps[1].title == "Package Seal & Unboxing"


def test_deterministic_apart_from_timings(videos, tmp_path):
    a = analyze_video(videos["moving"], "Return", evidence_dir=tmp_path / "ev")
    b = analyze_video(videos["moving"], "Return", evidence_dir=tmp_path / "ev")
    assert a.model_dump(exclude={"timings_ms"}) == b.model_dump(exclude={"timings_ms"})
    assert {"sampling", "detectors", "total"} <= a.timings_ms.keys()


def test_evidence_written_with_relative_paths(videos, tmp_path, monkeypatch):
    data_dir = tmp_path / "data"
    monkeypatch.setenv("VMS_DATA_DIR", str(data_dir))
    from vms.config import get_settings

    get_settings.cache_clear()
    evidence_dir = data_dir / "evidence" / "abc"
    r = analyze_video(videos["qr"], "Return", evidence_dir=evidence_dir)

    entries = [(s.key, e) for s in r.steps for e in s.evidence]
    assert entries, "the QR video should fire at least one step signal"
    for step in r.steps:
        assert len(step.evidence) <= 1
    for key, ev in entries:
        assert ev.image == f"evidence/abc/{key}_0.jpg"
        assert (data_dir / ev.image).is_file()
    assert r.steps[0].evidence[0].kind == "barcode"


def test_no_evidence_dir_means_no_files(videos):
    r = analyze_video(videos["qr"], "Return")
    assert all(e.image is None for s in r.steps for e in s.evidence)


def test_progress_callback(videos):
    seen: list[float] = []
    analyze_video(videos["qr"], "Return", progress_cb=seen.append)
    assert seen[-1] == 1.0
    assert seen == sorted(seen)
    assert len(seen) > 2


class _FakeReader:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, img):
        self.calls += 1
        return [[[0, 1, 0, 1]] * 7], [[]]


def test_ocr_runs_every_nth_valid_frame_and_on_label_onset(videos, monkeypatch):
    reader = _FakeReader()
    monkeypatch.setattr(ocr_mod, "get_ocr_reader", lambda: reader)
    monkeypatch.setattr("vms.analysis.detectors.heuristics.detect_label_region", lambda gray: False)
    r = analyze_video(videos["qr"], "Return")
    n_valid = r.quality.frames_ok
    assert reader.calls == len(range(0, n_valid, 3))
    assert r.metrics["avg_text_blocks"] == 7.0
    assert r.engine.detectors["ocr"] is True

    # Label onset on frames 1 and 5 (both off-cadence) adds exactly two OCR runs.
    reader.calls = 0
    labels = iter([False, True, False, False, False, True] + [False] * 100)
    monkeypatch.setattr(
        "vms.analysis.detectors.heuristics.detect_label_region", lambda gray: next(labels)
    )
    analyze_video(videos["qr"], "Return")
    assert reader.calls == len(range(0, n_valid, 3)) + 2
