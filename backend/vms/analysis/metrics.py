"""Aggregate per-frame signals into the flat metric dict that rubric checks reference."""

from vms.analysis.detectors import motion
from vms.analysis.detectors.base import FrameSignals
from vms.analysis.result import MetricValue

METRIC_KEYS = frozenset(
    {
        "label_ratio",
        "package_ratio",
        "tag_ratio",
        "product_ratio",
        "avg_text_blocks",
        "barcode_found",
        "barcode_count",
        "duration_s",
        "estimated_sides",
        "direction_changes",
        "motion_ratio",
        "end_activity_ratio",
        "max_label_hold_s",
        "quality_ok_ratio",
        "frames_sampled",
    }
)

# "Sealing near the end" = activity within the last quarter of the timeline.
END_FRACTION = 0.25


def _ratio(count: int, total: int) -> float:
    return round(count / total, 4) if total else 0.0


def _max_label_hold_s(signals: list[FrameSignals], interval_s: float) -> float:
    """Longest run of consecutive valid frames with a label and text visible.

    OCR doesn't run on every frame, so the last OCR text count carries forward.
    """
    best = run = 0
    text = 0
    for s in signals:
        if s.text_blocks is not None:
            text = s.text_blocks
        if s.valid and s.label and text > 0:
            run += 1
            best = max(best, run)
        else:
            run = 0
    return round(best * interval_s, 2)


def aggregate(
    signals: list[FrameSignals], duration_s: float, interval_s: float
) -> dict[str, MetricValue]:
    """Ratios use quality-valid frames as the denominator; motion uses every sampled frame."""
    n = len(signals)
    valid = [s for s in signals if s.valid]
    nv = len(valid)
    ocr_counts = [s.text_blocks for s in valid if s.text_blocks is not None]
    codes = {b.value for s in signals for b in s.barcodes}

    high = sum(1 for s in signals if s.motion_mag > motion.HIGH_MAGNITUDE)
    motion_ratio = _ratio(high, n)
    changes = motion.direction_changes([s.motion_dir for s in signals])
    tail_start = duration_s * (1 - END_FRACTION)
    tail = [s for s in signals if s.t_s >= tail_start]
    tail_active = sum(1 for s in tail if s.motion_mag >= motion.ACTIVE_MAGNITUDE)

    metrics: dict[str, MetricValue] = {
        "label_ratio": _ratio(sum(s.label for s in valid), nv),
        "package_ratio": _ratio(sum(s.package for s in valid), nv),
        "tag_ratio": _ratio(sum(s.tag for s in valid), nv),
        "product_ratio": _ratio(sum(s.product for s in valid), nv),
        "avg_text_blocks": round(sum(ocr_counts) / len(ocr_counts), 2) if ocr_counts else 0.0,
        "barcode_found": bool(codes),
        "barcode_count": len(codes),
        "duration_s": round(duration_s, 2),
        "estimated_sides": motion.estimated_sides(changes, motion_ratio, n),
        "direction_changes": changes,
        "motion_ratio": motion_ratio,
        "end_activity_ratio": _ratio(tail_active, len(tail)),
        "max_label_hold_s": _max_label_hold_s(signals, interval_s),
        "quality_ok_ratio": _ratio(nv, n),
        "frames_sampled": n,
    }
    return metrics
