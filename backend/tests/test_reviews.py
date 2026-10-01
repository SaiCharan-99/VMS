"""Review rules, the review queue, and review history (Phase 5)."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import auth
from tests.report_fixture import seed
from vms.db import session_scope
from vms.db.models import AuditLog, Role, Video


@pytest.fixture
def world(app, make_user):
    a, b = make_user(Role.operator), make_user(Role.operator)
    reviewer = make_user(Role.reviewer)
    ids = seed(a, b, reviewer)
    with TestClient(app, headers=auth(reviewer)) as c:
        yield {"ids": ids, "c": c, "reviewer": reviewer, "operator": a}


def _review(c, video_id, **body):
    return c.post(f"/api/v1/videos/{video_id}/reviews", json=body)


def test_review_sets_final_status_history_and_audit(world):
    c, v7 = world["c"], world["ids"]["v7"]
    r = _review(c, v7, final_status="pass", reason_code="false_negative_model")
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["reviewer_name"] == world["reviewer"].name
    assert body["comment"] is None  # model said review: no comment needed

    detail = c.get(f"/api/v1/videos/{v7}").json()
    assert detail["video"]["final_status"] == "pass"
    assert detail["video"]["human_reviewed"] is True
    assert [(h["final_status"], h["reason_code"]) for h in detail["reviews"]] == [
        ("pass", "false_negative_model")
    ]
    with session_scope() as s:
        entry = s.scalar(select(AuditLog).where(AuditLog.action == "review.created"))
        assert entry.entity_id == str(v7)
        assert entry.actor_user_id == world["reviewer"].id
        assert entry.data["model_status"] == "review"
        assert entry.data["reason_code"] == "false_negative_model"


def test_latest_review_wins(world):
    c, v7 = world["c"], world["ids"]["v7"]
    _review(c, v7, final_status="pass", reason_code="false_negative_model")
    _review(c, v7, final_status="fail", reason_code="label_unclear")
    detail = c.get(f"/api/v1/videos/{v7}").json()
    assert detail["video"]["final_status"] == "fail"
    assert len(detail["reviews"]) == 2  # append-only


@pytest.mark.parametrize(
    ("video", "decision", "reason", "needs_comment"),
    [
        ("v7", "fail", "other", True),  # `other` always needs one
        ("v7", "fail", "label_unclear", False),  # model abstained
        ("v2", "pass", "false_negative_model", True),  # overturns a model fail
        ("v2", "fail", "seal_not_shown", False),  # agrees with the model
        ("v1", "fail", "tags_not_shown", True),  # overturns a model pass
    ],
)
def test_comment_rules(world, video, decision, reason, needs_comment):
    c, vid = world["c"], world["ids"][video]
    r = _review(c, vid, final_status=decision, reason_code=reason, comment="  ")
    assert r.status_code == (422 if needs_comment else 201), r.text
    if needs_comment:
        assert "comment is required" in r.json()["detail"]
        ok = _review(c, vid, final_status=decision, reason_code=reason, comment="seen at 0:14")
        assert ok.status_code == 201


def test_review_validation(world, make_user):
    c, ids = world["c"], world["ids"]
    assert _review(c, ids["v7"], final_status="pass", reason_code="nope").status_code == 422
    assert _review(c, ids["v7"], final_status="review", reason_code="other").status_code == 422
    r = _review(c, ids["v6"], final_status="pass", reason_code="video_quality")
    assert r.status_code == 409  # no analysis yet
    assert _review(c, 99999, final_status="pass", reason_code="other").status_code == 404
    assert _review(c, ids["v9"], final_status="pass", reason_code="other").status_code == 404


def test_queue_oldest_first_with_filters(world):
    c, ids = world["c"], world["ids"]
    with session_scope() as s:  # put v3 back in the queue (it was reviewed in the fixture)
        s.get(Video, ids["v3"]).final_status = "review"
    items = c.get("/api/v1/review-queue").json()["items"]
    assert [v["id"] for v in items] == [ids["v3"], ids["v7"]]
    station = c.get("/api/v1/review-queue", params={"station_id": ids["S1"]}).json()
    assert station["total"] == 0
    forward = c.get("/api/v1/review-queue", params={"process_type": "Forward"}).json()
    assert forward["total"] == 0

    _review(c, ids["v7"], final_status="pass", reason_code="false_negative_model")
    assert [v["id"] for v in c.get("/api/v1/review-queue").json()["items"]] == [ids["v3"]]


def test_operator_cannot_review(app, world):
    with TestClient(app, headers=auth(world["operator"])) as c:
        r = _review(c, world["ids"]["v1"], final_status="pass", reason_code="other", comment="x")
    assert r.status_code == 403


def test_human_reviewed_flag_in_list(world):
    items = world["c"].get("/api/v1/videos", params={"page_size": 50}).json()["items"]
    flags = {v["original_filename"]: v["human_reviewed"] for v in items}
    assert flags["v4.mp4"] is True
    assert flags["v7.mp4"] is False
