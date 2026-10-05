"""Command line.

python -m vms.cli analyze <video> --process-type Return [--json out.json]
python -m vms.cli import-legacy --db audit_results.db
python -m vms.cli create-admin --email a@example.com --name "Ada"   # prompts (or --password-stdin)
python -m vms.cli seed-demo                                         # dev only
python -m vms.cli sop-doc --out docs/SOP.md                         # operator guide from rubrics
python -m vms.cli export-eval --out data/eval/labels.csv            # human reviews -> eval labels
python -m vms.cli openapi --out frontend/openapi.json             # API schema for type generation
python -m vms.cli purge --older-than-days 180 [--dry-run]           # retention file purge
"""

import argparse
import getpass
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


def _create_admin(args: argparse.Namespace) -> int:
    from vms.db import session_scope
    from vms.db.models import Role
    from vms.services import users

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("Password: ")
        if password != getpass.getpass("Repeat password: "):
            print("Passwords do not match.", file=sys.stderr)
            return 1
    try:
        with session_scope() as session:
            user = users.create(
                session, email=args.email, name=args.name, password=password, role=Role.admin
            )
            print(f"Created admin {user.email} (id {user.id}).")
    except users.UserError as exc:
        print(exc.detail, file=sys.stderr)
        return 1
    return 0


def _seed_demo(args: argparse.Namespace) -> int:
    from vms.db import session_scope
    from vms.services.demo import DEMO_USERS, seed_demo

    if get_settings().env != "dev":
        print("seed-demo only runs with VMS_ENV=dev.", file=sys.stderr)
        return 1
    with session_scope() as session:
        created = seed_demo(session)
    print(f"Demo data ready ({created} new users). Dev-only logins:")
    for email, _name, role, password in DEMO_USERS:
        print(f"  {role.value:<9} {email:<22} {password}")
    return 0


def _sop_doc(args: argparse.Namespace) -> int:
    from vms.sop_doc import render

    text = render()
    if args.out:
        args.out.write_text(text, encoding="utf-8", newline="\n")
        print(f"Wrote {args.out}")
    else:
        sys.stdout.write(text)
    return 0


def _export_eval(args: argparse.Namespace) -> int:
    from vms.db import session_scope
    from vms.evaluation.export import export_reviewed
    from vms.evaluation.labels import write_labels

    with session_scope() as session:
        rows, skipped = export_reviewed(session)
    write_labels(args.out, rows)
    print(f"Wrote {len(rows)} labelled videos to {args.out} ({skipped} skipped: file missing).")
    return 0


def _purge(args: argparse.Namespace) -> int:
    from vms.db import session_scope
    from vms.services.retention import purge
    from vms.storage import get_storage

    days = args.older_than_days or get_settings().retention_days
    if not days or days < 1:
        print("Pass --older-than-days N (N >= 1) or set VMS_RETENTION_DAYS.", file=sys.stderr)
        return 1
    with session_scope() as session:
        report = purge(session, get_storage(), days, dry_run=args.dry_run)
    verb = "Would delete" if args.dry_run else "Deleted"
    mb = report.bytes_freed / 1024 / 1024
    print(f"{verb} {report.purged} video files older than {days} days ({mb:.1f} MB).")
    return 0


def _openapi(args: argparse.Namespace) -> int:
    import json

    from vms.api.main import create_app

    text = json.dumps(create_app().openapi(), indent=2, sort_keys=True) + "\n"
    args.out.write_text(text, encoding="utf-8", newline="\n")
    print(f"Wrote {args.out}")
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

    p = sub.add_parser("create-admin", help="Create an admin user (prompts for the password)")
    p.add_argument("--email", required=True)
    p.add_argument("--name", required=True)
    p.add_argument(
        "--password-stdin", action="store_true", help="read the password from stdin (scripts)"
    )
    p.set_defaults(func=_create_admin)

    p = sub.add_parser("seed-demo", help="Dev only: demo warehouse, stations, one user per role")
    p.set_defaults(func=_seed_demo)

    p = sub.add_parser("sop-doc", help="Render the operator SOP guide from the rubric YAML")
    p.add_argument("--out", type=Path, help="write here instead of stdout (docs/SOP.md)")
    p.set_defaults(func=_sop_doc)

    p = sub.add_parser("export-eval", help="Write human-reviewed videos as an eval labels CSV")
    p.add_argument("--out", type=Path, default=Path("data/eval/labels.csv"))
    p.set_defaults(func=_export_eval)

    p = sub.add_parser("purge", help="Retention: delete old video files (rows/evidence kept)")
    p.add_argument("--older-than-days", type=int, help="default: VMS_RETENTION_DAYS")
    p.add_argument("--dry-run", action="store_true", help="only count what would be deleted")
    p.set_defaults(func=_purge)

    p = sub.add_parser("openapi", help="Write the OpenAPI schema (frontend type generation)")
    p.add_argument("--out", type=Path, default=Path("frontend/openapi.json"))
    p.set_defaults(func=_openapi)

    args = parser.parse_args(argv)
    configure_logging()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
