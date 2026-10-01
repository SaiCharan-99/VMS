"""Reviewer-style one-paragraph summary (ported from app.py `manual_summary`)."""

from vms.analysis.result import StepResult


def render(
    process_type: str, decision: str, steps: list[StepResult], barcode: bool, confidence: float
) -> str:
    pct = {s.key: round(s.score / s.weight * 100) if s.weight else 0 for s in steps}
    names = {s.key: s.title.lower() for s in steps}
    strongest = max(pct, key=pct.__getitem__)
    weakest = min(pct, key=pct.__getitem__)
    text = (
        f"{decision.lower().capitalize()} after reviewing the {process_type.lower()} recording. "
        f"The strongest area was the {names[strongest]} ({pct[strongest]}%). "
        f"The main area needing attention is the {names[weakest]} ({pct[weakest]}%)."
    )
    if barcode:
        text += " The barcode was readable in the recording."
    else:
        text += " The barcode was not confirmed clearly in the recording."
    return text + f" Confidence in this review was {round(confidence * 100)}%."
