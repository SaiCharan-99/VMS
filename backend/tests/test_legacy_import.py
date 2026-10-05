import json
import sqlite3

from vms.cli import main as cli_main
from vms.db import session_scope
from vms.services.legacy_import import import_legacy

ROWS = [("a.mp4", "pass", 90, "AWB-9"), ("b.mp4", "fail", 20, None)]


def _legacy_db(path):
    conn = sqlite3.connect(path)
    conn.execute(
        "CREATE TABLE results (id INTEGER PRIMARY KEY AUTOINCREMENT, uploaded_at TEXT NOT NULL,"
        " file_name TEXT NOT NULL, process_type TEXT NOT NULL, status TEXT NOT NULL,"
        " decision TEXT NOT NULL, confidence REAL NOT NULL, total_score INTEGER NOT NULL,"
        " result_json TEXT NOT NULL)"
    )
    for name, status, score, barcode in ROWS:
        result = {"total_score": score, "status": status, "detected_barcode": barcode}
        conn.execute(
            "INSERT INTO results (uploaded_at, file_name, process_type, status, decision,"
            " confidence, total_score, result_json) VALUES (?, ?, 'Return', ?, ?, 0.8, ?, ?)",
            ("2026-09-01 10:00:00", name, status, status, score, json.dumps(result)),
        )
    conn.commit()
    conn.close()


def test_import_is_idempotent(client, tmp_path):
    db = tmp_path / "audit_results.db"
    _legacy_db(db)
    with session_scope() as s:
        assert import_legacy(s, db) == (2, 0)
    assert cli_main(["import-legacy", "--db", str(db)]) == 0  # nothing new
    with session_scope() as s:
        assert import_legacy(s, db) == (0, 2)

    page = client.get("/api/v1/videos", params={"sort": "created_at"}).json()
    assert page["total"] == 2
    a = next(v for v in page["items"] if v["original_filename"] == "a.mp4")
    assert (a["source"], a["awb"], a["final_status"], a["stream_url"]) == (
        "legacy",
        "AWB-9",
        "pass",
        None,
    )
    detail = client.get(f"/api/v1/videos/{a['id']}").json()
    assert detail["analysis"]["schema_version"] == "1.0"
    assert detail["analysis"]["result"]["detected_barcode"] == "AWB-9"
    assert client.post(f"/api/v1/videos/{a['id']}/reanalyze").status_code == 409
