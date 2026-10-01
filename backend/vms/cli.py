"""Command line.

python -m vms.cli analyze <video> --process-type Return [--json out.json]
python -m vms.cli import-legacy --db audit_results.db
"""

import argparse
import sys
import uuid
from pathlib import Path

from vms.analysis import analyze_video
from vms.config import get_settings
from vms.logging import configure_logging


def _analyze(args: argparse.Namespace) -> int:
    evidence_dir = args.evidence_dir
    if evidence_dir is None and not args.no_evidence:
        evidence_dir = get_settings().data_dir / "evidence" / uuid.uuid4().hex
    result = analyze_video(args.video, args.process_type, evidence_dir=evidence_dir)
    payload = result.model_dump_json(indent=2)
    if args.json:
        args.json.write_text(payload, encoding="utf-8")
        print(f"{result.status.upper()} {result.total_score}/100 conf={result.confidence:.2f}")
        print(f"Result written to {args.json}")
    else:
        print(payload)
    if evidence_dir is not None:
        print(f"Evidence frames in {evidence_dir}", file=sys.stderr)
    return 0


def _import_legacy(args: argparse.Namespace) -> int:
    from vms.db import session_scope
    from vms.services.legacy_import import import_legacy

    with session_scope() as session:
        imported, skipped = import_legacy(session, args.db)
    print(f"Imported {imported} legacy results, skipped {skipped} already imported.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="vms.cli")
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("analyze", help="Score one video against the SOP rubric")
    p.add_argument("video", type=Path)
    p.add_argument("--process-type", choices=["Forward", "Return"], default="Return")
    p.add_argument("--json", type=Path, help="write the result here instead of stdout")
    p.add_argument("--evidence-dir", type=Path, help="default: <data_dir>/evidence/<random id>")
    p.add_argument("--no-evidence", action="store_true", help="don't save evidence frames")
    p.set_defaults(func=_analyze)

    p = sub.add_parser("import-legacy", help="Import the pre-Phase-2 audit_results.db")
    p.add_argument("--db", type=Path, default=Path("audit_results.db"))
    p.set_defaults(func=_import_legacy)

    args = parser.parse_args(argv)
    configure_logging()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
