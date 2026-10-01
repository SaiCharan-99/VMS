"""Eval label files: one human-judged video per row."""

import csv
from dataclasses import dataclass, field
from pathlib import Path

PROCESS_TYPES = ("Forward", "Return")
STATUSES = ("pass", "review", "fail")
STEP_STATUSES = ("met", "partial", "missed")
# Column -> rubric step position (Forward's second step, "packing", uses the `unboxing` column).
STEP_COLUMNS = ("shipping_label", "unboxing", "tags", "product")
COLUMNS = ("video_path", "process_type", "expected_status", *STEP_COLUMNS, "notes")


class LabelError(ValueError):
    pass


@dataclass(frozen=True)
class LabelRow:
    video: Path
    process_type: str
    expected_status: str
    steps: dict[str, str] = field(
        default_factory=dict
    )  # column -> met|partial|missed (may be partial)
    notes: str = ""


def _choice(value: str, allowed: tuple[str, ...], what: str, line: int) -> str:
    value = value.strip()
    if value not in allowed:
        raise LabelError(f"line {line}: {what} must be one of {', '.join(allowed)}, got {value!r}")
    return value


def read_labels(path: Path) -> list[LabelRow]:
    """Relative video paths resolve against the labels file's folder, then the working directory."""
    path = Path(path)
    rows: list[LabelRow] = []
    with path.open(newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        missing = {"video_path", "process_type", "expected_status"} - set(reader.fieldnames or [])
        if missing:
            raise LabelError(f"{path}: missing columns {sorted(missing)}")
        for line, rec in enumerate(reader, start=2):
            if not (rec.get("video_path") or "").strip():
                continue
            video = Path(rec["video_path"].strip())
            if not video.is_absolute():
                beside = path.parent / video
                video = beside if beside.exists() else video
            steps = {
                col: _choice(rec[col], STEP_STATUSES, col, line)
                for col in STEP_COLUMNS
                if (rec.get(col) or "").strip()
            }
            rows.append(
                LabelRow(
                    video=video,
                    process_type=_choice(rec["process_type"], PROCESS_TYPES, "process_type", line),
                    expected_status=_choice(
                        rec["expected_status"], STATUSES, "expected_status", line
                    ),
                    steps=steps,
                    notes=(rec.get("notes") or "").strip(),
                )
            )
    return rows


def write_labels(path: Path, rows: list[LabelRow]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(COLUMNS)
        for r in rows:
            writer.writerow(
                [
                    r.video,
                    r.process_type,
                    r.expected_status,
                    *(r.steps.get(c, "") for c in STEP_COLUMNS),
                    r.notes,
                ]
            )
