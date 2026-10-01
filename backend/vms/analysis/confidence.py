"""How much the evidence can be trusted (0..1), independent of the rubric score."""

from vms.analysis.result import MetricValue


def compute(metrics: dict[str, MetricValue]) -> float:
    """Weights carried over from the v1 analyzer; quality uses all sampled frames."""
    if not metrics.get("frames_sampled"):
        return 0.0
    confidence = (
        0.35 * float(metrics["quality_ok_ratio"])
        + 0.25 * float(metrics["package_ratio"])
        + 0.20 * float(metrics["label_ratio"])
        + 0.10 * float(metrics["product_ratio"])
        + 0.10 * (1.0 if metrics["barcode_found"] else 0.4)
    )
    return round(max(0.1, min(1.0, confidence)), 3)
