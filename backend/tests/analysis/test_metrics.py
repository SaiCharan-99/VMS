from vms.analysis import confidence
from vms.analysis.detectors.base import BarcodeHit, FrameSignals
from vms.analysis.detectors.motion import direction_changes, estimated_sides
from vms.analysis.metrics import METRIC_KEYS, aggregate


def _sig(t: float, valid: bool = True, **kw) -> FrameSignals:
    return FrameSignals(t_s=t, valid=valid, **kw)


def test_empty_signals():
    m = aggregate([], 0.0, 1 / 3)
    assert m.keys() == METRIC_KEYS
    assert m["frames_sampled"] == 0
    assert m["estimated_sides"] == 0
    assert m["direction_changes"] == 0
    assert m["barcode_found"] is False
    assert confidence.compute(m) == 0.0


def test_ratios_use_valid_frames_only():
    signals = [
        _sig(0, label=True, package=True),
        _sig(1, package=True),
        _sig(2, valid=False, label=True, tag=True),
        _sig(3, valid=False),
    ]
    m = aggregate(signals, 4.0, 1.0)
    assert m.keys() == METRIC_KEYS
    assert m["label_ratio"] == 0.5
    assert m["package_ratio"] == 1.0
    assert m["tag_ratio"] == 0.0
    assert m["quality_ok_ratio"] == 0.5


def test_barcodes_and_text():
    signals = [
        _sig(0, barcodes=[BarcodeHit("A", "QRCODE")], text_blocks=4),
        _sig(1, barcodes=[BarcodeHit("A", "QRCODE"), BarcodeHit("B", "CODE128")]),
        _sig(2, text_blocks=8),
    ]
    m = aggregate(signals, 3.0, 1.0)
    assert m["barcode_found"] is True
    assert m["barcode_count"] == 2
    assert m["avg_text_blocks"] == 6.0  # averaged over frames where OCR ran


def test_max_label_hold_carries_text_forward():
    signals = [
        _sig(0, label=True, text_blocks=3),
        _sig(0.5, label=True),
        _sig(1.0, label=True),
        _sig(1.5, label=False),
        _sig(2.0, label=True),
        _sig(2.5, label=True, text_blocks=0),
    ]
    assert aggregate(signals, 3.0, 0.5)["max_label_hold_s"] == 1.5


def test_direction_changes_hysteresis():
    assert direction_changes([]) == 0
    assert direction_changes([1, 0, 1]) == 1  # still frames don't break a run
    assert direction_changes([1, -1, 1, -1]) == 0  # jitter never settles
    assert direction_changes([1, 1, -1, -1, 1, 1]) == 3


def test_estimated_sides_clamped():
    assert estimated_sides(0, 0.0, 0) == 0
    assert estimated_sides(0, 0.0, 5) == 1
    assert estimated_sides(2, 0.5, 5) == 5
    assert estimated_sides(9, 0.5, 5) == 6


def test_end_activity_ratio():
    signals = [_sig(t, motion_mag=0.0) for t in range(8)]
    for s in signals[6:]:
        s.motion_mag = 1.0
    assert aggregate(signals, 8.0, 1.0)["end_activity_ratio"] == 1.0
