"""Report math against a hand calculation on `report_fixture` (acceptance 2), plus the CSV."""

import csv
import io

import pytest

from tests.conftest import auth
from tests.report_fixture import seed
from vms.db.models import Role

RANGE = {"date_from": "2026-09-10", "date_to": "2026-09-12"}


@pytest.fixture
def world(make_user):
    a = make_user(Role.operator)
    b = make_user(Role.operator)
    reviewer = make_user(Role.reviewer)
    ids = seed(a, b, reviewer)
    return {"ids": ids, "a": a, "b": b, "reviewer": reviewer}


def test_summary_matches_hand_calculation(client, world):
    r = client.get("/api/v1/reports/summary", params=RANGE)
    assert r.status_code == 200, r.text
    s = r.json()
    # v1..v7 are in range; v8 is before it and v9 is deleted.
    assert s["totals"] == {"total": 7, "pass": 3, "review": 1, "fail": 2, "pending": 1}
    assert s["analyzed"] == 6
    assert s["pass_rate"] == 0.5  # 3 / 6
    assert s["review_rate"] == 0.3333  # model said review on v3, v7
    assert s["reviewed"] == 3  # v3, v4, v5
    # v3's model said review (excluded); v4 fail→pass disagrees; v5 fail→fail agrees.
    assert s["agreement_n"] == 2
    assert s["agreement_rate"] == 0.5
    assert s["avg_score"] == 53.33  # (90+30+60+40+45+55) / 6
    assert s["avg_turnaround_s"] == 1236.0  # (60+120+3600+1800+600) / 5

    checks = [(c["process_type"], c["check_key"], c["failures"], c["evaluated"], c["rate"])
              for c in s["top_failed_checks"]]  # fmt: skip
    assert checks == [
        ("Return", "barcode_read", 3, 3, 1.0),
        ("Forward", "product_visible", 2, 3, 0.6667),
        ("Forward", "barcode_read", 1, 3, 0.3333),
    ]
    assert s["top_failed_checks"][0]["step_title"] == "Shipping Label & Barcode"
    assert s["top_failed_checks"][0]["note"] == "barcode_read note"

    days = {g["key"]: (g["total"], g["pass"], g["review"], g["fail"], g["pending"])
            for g in s["groups"]}  # fmt: skip
    assert days == {
        "2026-09-10": (3, 2, 0, 1, 0),
        "2026-09-11": (4, 1, 1, 1, 1),
        "2026-09-12": (0, 0, 0, 0, 0),  # gap-filled
    }
    assert [g["key"] for g in s["groups"]] == sorted(days)


def test_group_by_station_and_operator(client, world):
    s = client.get("/api/v1/reports/summary", params={**RANGE, "group_by": "station"}).json()
    by_label = {g["label"]: (g["total"], g["pass_rate"], g["avg_score"]) for g in s["groups"]}
    assert by_label == {
        "S1": (3, 0.3333, 55.0),  # v1 pass, v2 fail, v5 fail; (90+30+45)/3
        "S2": (3, 0.6667, 51.67),  # v3 pass, v4 pass, v7 review; (60+40+55)/3
        "No station": (1, None, None),  # v6 pending
    }

    s = client.get("/api/v1/reports/summary", params={**RANGE, "group_by": "operator"}).json()
    totals = {g["key"]: g["total"] for g in s["groups"]}
    assert totals == {str(world["a"].id): 3, str(world["b"].id): 4}


def test_filters_and_timezone(client, world):
    s = client.get("/api/v1/reports/summary", params={**RANGE, "process_type": "Return"}).json()
    assert s["totals"]["total"] == 3

    # UTC+12: v3 (d1 12:00 UTC) moves to local d2; v8 (d0 08:00) stays before the range.
    s = client.get("/api/v1/reports/summary", params={**RANGE, "tz_offset_min": 720}).json()
    days = {g["key"]: g["total"] for g in s["groups"]}
    assert days["2026-09-10"] == 2
    assert days["2026-09-11"] == 4  # v3, v4, v5, v6 (v7 is d2 12:00 UTC → local d3)
    assert days["2026-09-12"] == 1


def test_summary_validates_range(client, db_ready):
    r = client.get(
        "/api/v1/reports/summary", params={"date_from": "2026-09-12", "date_to": "2026-09-10"}
    )
    assert r.status_code == 400
    assert client.get("/api/v1/reports/summary").json()["groups"].__len__() == 7  # default week


def test_csv_export(client, world):
    r = client.get("/api/v1/reports/export.csv", params={"date_from": "2026-09-10"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    raw = r.content
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 BOM for Excel
    rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
    header = list(rows[0])
    for col in ("Timestamp", "File", "Process Type", "Verdict", "Manual Summary", "Score %",
                "Shipping Label & Barcode %", "Product Condition %", "Sides", "Duration (s)",
                "Follow-up Notes", "AWB", "Station", "Operator", "Final Status", "Reviewer",
                "Review Reason"):  # fmt: skip
        assert col in header

    assert [row["File"] for row in rows] == [f"v{i}.mp4" for i in range(1, 8)]  # oldest first
    v4 = rows[3]
    assert v4["Verdict"] == "fail"
    assert v4["Final Status"] == "pass"
    assert v4["Reviewer"] == world["reviewer"].name
    assert v4["Review Reason"] == "false_negative_model"
    assert v4["Score %"] == "40%"
    assert v4["Shipping Label & Barcode %"] == "0%"
    assert v4["Product Condition %"] == "100%"
    assert v4["Station"] == "S2"
    assert v4["Sides"] == "4/6"
    assert rows[1]["Follow-up Notes"] == "Product not visible enough"
    pending = rows[5]
    assert (pending["Verdict"], pending["Score %"], pending["Final Status"]) == ("", "", "pending")


def test_csv_respects_video_filters(client, world):
    r = client.get("/api/v1/reports/export.csv", params={"status": "fail"})
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert [row["File"] for row in rows] == ["v2.mp4", "v5.mp4"]


def test_csv_streams_in_batches(client, world, monkeypatch):
    from vms.services import reports

    original = reports.stream_csv
    monkeypatch.setattr(reports, "stream_csv", lambda s, stmt, tz=0: original(s, stmt, tz, batch=2))
    r = client.get("/api/v1/reports/export.csv")
    rows = list(csv.DictReader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len(rows) == 8  # v1..v8 (v9 deleted)


def test_reports_need_reviewer(app, world):
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        r = c.get("/api/v1/reports/summary", headers=auth(world["a"]))
    assert r.status_code == 403
