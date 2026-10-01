# ruff: noqa: E501  (the fixture table is easier to check by hand on one line per video)
"""A small, hand-countable world for review and report tests.

Day 1 = 2026-09-10, day 2 = 2026-09-11 (UTC). Each analysis has two checks:
`shipping_label/barcode_read` and `product/product_visible`.

| video | type    | station | day/time | model (score)  | failed checks          | review (at)          | final   |
|-------|---------|---------|----------|----------------|------------------------|----------------------|---------|
| v1    | Forward | S1      | d1 10:00 | pass (90) +60s | -                      | -                    | pass    |
| v2    | Forward | S1      | d1 11:00 | fail (30) +120s| barcode, product       | -                    | fail    |
| v3    | Return  | S2      | d1 12:00 | review (60)    | barcode                | pass (+3600s)        | pass    |
| v4    | Return  | S2      | d2 09:00 | fail (40)      | barcode                | pass (+1800s)        | pass    |
| v5    | Forward | S1      | d2 10:00 | fail (45)      | product                | fail (+600s)         | fail    |
| v6    | Forward | -       | d2 11:00 | (none)         | -                      | -                    | pending |
| v7    | Return  | S2      | d2 12:00 | review (55)    | barcode                | -                    | review  |
| v8    | Forward | S1      | d0 08:00 | pass (95)      | -                      | -                    | pass    |  (before range)
| v9    | Forward | S1      | d1 09:00 | pass (99)      | -                      | -                    | pass    |  (deleted)
"""

from datetime import datetime, timedelta

from vms.db import session_scope
from vms.db.models import (
    Analysis,
    FinalStatus,
    ProcessType,
    Review,
    ReviewStatus,
    Station,
    User,
    Video,
    VideoSource,
    Warehouse,
)

D0, D1, D2 = datetime(2026, 9, 9), datetime(2026, 9, 10), datetime(2026, 9, 11)


def result_json(process_type: str, status: str, score: int, failed: set[str]) -> dict:
    def check(key: str) -> dict:
        ok = key not in failed
        return {
            "key": key,
            "passed": ok,
            "points": 15 if ok else 0,
            "max_points": 15,
            "metric": "m",
            "value": 1,
            "threshold": 1,
            "note": None if ok else f"{key} note",
        }

    return {
        "schema_version": "2.0",
        "process_type": process_type,
        "summary": f"{status} summary",
        "metrics": {"estimated_sides": 4},
        "steps": [
            {
                "key": "shipping_label",
                "title": "Shipping Label & Barcode",
                "weight": 30,
                "score": 15 if "barcode_read" not in failed else 0,
                "status": "pass",
                "checks": [check("barcode_read")],
                "notes": [],
                "evidence": [],
            },
            {
                "key": "product",
                "title": "Product Condition",
                "weight": 25,
                "score": 25 if "product_visible" not in failed else 0,
                "status": "pass",
                "checks": [check("product_visible")],
                "notes": ["Product not visible enough."] if "product_visible" in failed else [],
                "evidence": [],
            },
        ],
    }


def seed(operator_a: User, operator_b: User, reviewer: User) -> dict[str, int]:
    """Insert the table above. Returns name -> id (videos and stations)."""
    ids: dict[str, int] = {}
    with session_scope() as s:
        wh = Warehouse(code="WH", name="WH")
        s.add(wh)
        s.flush()
        s1, s2 = (
            Station(warehouse_id=wh.id, code="S1", name="S1"),
            Station(warehouse_id=wh.id, code="S2", name="S2"),
        )
        s.add_all([s1, s2])
        s.flush()
        ids.update(S1=s1.id, S2=s2.id)

        rows = [
            # name, type, station, op, created, (status, score, failed, +s), review, deleted
            ("v1", "Forward", s1, operator_a, D1 + timedelta(hours=10), ("pass", 90, set(), 60), None, False),
            ("v2", "Forward", s1, operator_a, D1 + timedelta(hours=11), ("fail", 30, {"barcode_read", "product_visible"}, 120), None, False),
            ("v3", "Return", s2, operator_b, D1 + timedelta(hours=12), ("review", 60, {"barcode_read"}, 30), ("pass", 3600), False),
            ("v4", "Return", s2, operator_b, D2 + timedelta(hours=9), ("fail", 40, {"barcode_read"}, 30), ("pass", 1800), False),
            ("v5", "Forward", s1, operator_a, D2 + timedelta(hours=10), ("fail", 45, {"product_visible"}, 30), ("fail", 600), False),
            ("v6", "Forward", None, operator_b, D2 + timedelta(hours=11), None, None, False),
            ("v7", "Return", s2, operator_b, D2 + timedelta(hours=12), ("review", 55, {"barcode_read"}, 30), None, False),
            ("v8", "Forward", s1, operator_a, D0 + timedelta(hours=8), ("pass", 95, set(), 30), None, False),
            ("v9", "Forward", s1, operator_a, D1 + timedelta(hours=9), ("pass", 99, set(), 30), None, True),
        ]  # fmt: skip
        for name, ptype, station, op, created, model, review, deleted in rows:
            video = Video(
                original_filename=f"{name}.mp4",
                storage_key=f"videos/{name}.mp4",
                process_type=ProcessType(ptype),
                awb=f"AWB-{name}",
                uploaded_by=op.id,
                station_id=station.id if station else None,
                source=VideoSource.web,
                duration_s=12.5,
                created_at=created,
                deleted_at=created if deleted else None,
                final_status=FinalStatus.pending,
            )
            s.add(video)
            s.flush()
            ids[name] = video.id
            if model is None:
                continue
            status, score, failed, after = model
            analysis = Analysis(
                video_id=video.id,
                schema_version="2.0",
                engine_version="test",
                rubric_id=f"{ptype.lower()}-v1",
                total_score=score,
                confidence=0.8,
                status=status,
                decision=status,
                result_json=result_json(ptype, status, score, failed),
                created_at=created + timedelta(seconds=after),
            )
            s.add(analysis)
            s.flush()
            video.final_status = FinalStatus(status)
            if review is not None:
                decision, review_after = review
                s.add(
                    Review(
                        analysis_id=analysis.id,
                        video_id=video.id,
                        reviewer_id=reviewer.id,
                        final_status=ReviewStatus(decision),
                        reason_code="false_negative_model"
                        if decision == "pass"
                        else "seal_not_shown",
                        comment="checked by hand",
                        created_at=created + timedelta(seconds=review_after),
                    )
                )
                video.final_status = FinalStatus(decision)
    return ids
