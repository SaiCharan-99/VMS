"""Import rows from the pre-Phase-2 `audit_results.db` (`results` table) as legacy videos."""

import json
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from vms.db.models import Analysis, FinalStatus, ProcessType, Video, VideoSource, utcnow
from vms.services import audit

_NAMESPACE = uuid.UUID("5d0c2f8e-9a4b-4c1e-8f43-3b1a6e0d7c21")


def _legacy_uuid(row: sqlite3.Row) -> str:
    """Stable per source row, so re-running the import skips what is already there."""
    return uuid.uuid5(_NAMESPACE, f"{row['id']}|{row['uploaded_at']}|{row['file_name']}").hex


def _parse_ts(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return utcnow()


def import_legacy(session: Session, db_path: Path) -> tuple[int, int]:
    """Returns (imported, skipped). Videos get `source=legacy` and no file."""
    if not db_path.exists():
        raise FileNotFoundError(db_path)
    src = sqlite3.connect(f"file:{db_path.as_posix()}?mode=ro", uri=True)
    src.row_factory = sqlite3.Row
    try:
        rows = src.execute("SELECT * FROM results ORDER BY id").fetchall()
    finally:
        src.close()

    imported = skipped = 0
    for row in rows:
        video_uuid = _legacy_uuid(row)
        if session.scalar(select(Video.id).where(Video.uuid == video_uuid)) is not None:
            skipped += 1
            continue
        result = json.loads(row["result_json"])
        created = _parse_ts(row["uploaded_at"])
        status = row["status"] if row["status"] in {"pass", "review", "fail"} else "review"
        video = Video(
            uuid=video_uuid,
            original_filename=row["file_name"],
            process_type=ProcessType(row["process_type"]),
            awb=result.get("detected_barcode") or None,
            source=VideoSource.legacy,
            duration_s=result.get("duration_s"),
            created_at=created,
            final_status=FinalStatus(status),
        )
        session.add(video)
        session.flush()
        session.add(
            Analysis(
                video_id=video.id,
                schema_version="1.0",
                engine_version="legacy",
                rubric_id="legacy-v1",
                total_score=int(row["total_score"]),
                confidence=float(row["confidence"]),
                status=status,
                decision=row["decision"],
                barcodes=result.get("detected_barcode") or "",
                result_json=result,
                created_at=created,
            )
        )
        imported += 1
    audit.log(
        session,
        "legacy.imported",
        "video",
        None,
        {"source": str(db_path), "imported": imported, "skipped": skipped},
    )
    return imported, skipped
