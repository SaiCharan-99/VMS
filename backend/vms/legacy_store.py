"""SQLite store for v1 analysis results. Phase 2 imports these rows into the new schema."""

import json
import sqlite3
from pathlib import Path

from vms.config import get_settings


class AuditStore:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else get_settings().sqlite_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    uploaded_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    process_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    decision TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    total_score INTEGER NOT NULL,
                    result_json TEXT NOT NULL
                )
                """
            )

    def save(self, file_name: str, process_type: str, analysis: dict) -> int:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO results (uploaded_at, file_name, process_type, status, decision,
                                     confidence, total_score, result_json)
                VALUES (datetime('now'), ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    file_name,
                    process_type,
                    analysis.get("status", "review"),
                    analysis.get("decision", "Review Required"),
                    float(analysis.get("confidence", 0.0)),
                    int(analysis.get("total_score", 0)),
                    json.dumps(analysis),
                ),
            )
            return int(cursor.lastrowid)

    def list_recent(self, limit: int = 20) -> list[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM results ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            return [dict(row) for row in rows]
