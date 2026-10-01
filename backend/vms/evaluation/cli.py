"""Entry points behind ml/evaluate.py and ml/calibrate.py."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from vms.analysis.rubric import Rubric, active_rubric_ids, get_rubric
from vms.config import get_settings
from vms.evaluation import calibrate, report
from vms.evaluation.labels import LabelError, LabelRow, read_labels
from vms.evaluation.runner import Measured, measure


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--labels", type=Path, required=True, help="CSV: see ml/eval_labels.example.csv")
    p.add_argument(
        "--rubric",
        help="comma-separated rubric ids, one per process type (default: the active rubrics)",
    )
    p.add_argument("--weights", type=Path, help="YOLO weights (default: VMS_YOLO_WEIGHTS)")
    p.add_argument("--out-dir", type=Path, default=Path("data/eval"))
    p.add_argument("--from-cache", action="store_true", help="never run the CV pipeline")


def _rubrics(arg: str | None) -> dict[str, Rubric]:
    chosen = {pt: get_rubric(rid) for pt, rid in active_rubric_ids().items()}
    for rid in (arg or "").split(","):
        if rid.strip():
            rubric = get_rubric(rid.strip())
            chosen[rubric.process_type] = rubric
    return chosen


def _load(args: argparse.Namespace) -> tuple[list[LabelRow], list[Measured]]:
    if args.weights:
        # Settings are cached, so the override has to land before the first get_settings().
        import os

        os.environ["VMS_YOLO_WEIGHTS"] = str(args.weights)
        get_settings.cache_clear()
    rows = read_labels(args.labels)
    missing = [r.video for r in rows if not r.video.is_file()]
    if missing:
        raise LabelError(f"videos not found: {', '.join(map(str, missing[:5]))}")
    cache = args.out_dir / "cache"
    rows_ok, measured = [], []
    for i, row in enumerate(rows, 1):
        m = measure(row, cache, cache_only=args.from_cache)
        if m is None:
            print(f"[{i}/{len(rows)}] {row.video.name}: not cached, skipped", file=sys.stderr)
            continue
        print(
            f"[{i}/{len(rows)}] {row.video.name}: {'cached' if m.cached else f'{m.runtime_ms} ms'}",
            file=sys.stderr,
        )
        rows_ok.append(row)
        measured.append(m)
    return rows_ok, measured


def evaluate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ml/evaluate.py", description=__doc__)
    _add_common(parser)
    args = parser.parse_args(argv)
    try:
        rows, measured = _load(args)
    except (LabelError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if not rows:
        print("error: no videos to evaluate", file=sys.stderr)
        return 1
    rep = report.build_report(rows, measured, _rubrics(args.rubric))
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / f"report_{stamp}.json").write_text(
        json.dumps(report.to_json(rep), indent=2), encoding="utf-8"
    )
    md = report.render_markdown(rep, args.labels.name)
    (args.out_dir / f"report_{stamp}.md").write_text(md, encoding="utf-8")
    print(md)
    print(f"Wrote {args.out_dir / f'report_{stamp}.md'}")
    return 0


def calibrate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ml/calibrate.py", description=calibrate.__doc__)
    _add_common(parser)
    parser.add_argument("--min-videos", type=int, default=30, help="warn below this many labels")
    args = parser.parse_args(argv)
    args.from_cache = True if not args.from_cache else args.from_cache  # never re-run the CV here
    try:
        rows, measured = _load(args)
    except (LabelError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    for process_type, rubric in _rubrics(args.rubric).items():
        samples = [
            (m.metrics, r.expected_status)
            for r, m in zip(rows, measured, strict=True)
            if r.process_type == process_type
        ]
        if not samples:
            continue
        if len(samples) < args.min_videos:
            print(
                f"warning: only {len(samples)} {process_type} videos; thresholds fitted on so "
                "few labels will not generalise.",
                file=sys.stderr,
            )
        s = calibrate.suggest(rubric, samples)
        print(
            f"{rubric.id}: false passes {s.before[0]} -> {s.after[0]}, "
            f"review + false fails {s.before[1]} -> {s.after[1]} (n={s.n})"
        )
        if not s.changes:
            print("  no change improves on the current thresholds.")
            continue
        for label, old, new in s.changes:
            print(f"  {label}: {old} -> {new}")
        path = args.out_dir / f"calibration_{rubric.id}_{stamp}.diff"
        path.write_text(s.diff, encoding="utf-8")
        print(f"  Suggested diff written to {path}. Copy it into a new rubric file by hand.")
    return 0
