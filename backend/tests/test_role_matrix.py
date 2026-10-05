"""Every route x every caller kind -> allowed, 401, or 403 (IMPLEMENTATION.md §8).

"ok" means the guard let the request through: the handler may still answer 2xx, 400, 404,
or 422 (the bodies sent here are deliberately minimal).
"""

import pytest
from fastapi.testclient import TestClient

from tests.conftest import TEST_PASSWORD, auth
from vms.db import session_scope
from vms.db.models import (
    Analysis,
    EvidenceItem,
    Job,
    ProcessType,
    Role,
    Video,
    VideoSource,
    Warehouse,
)

CALLERS = ("anon", "operator", "reviewer", "admin", "api_key")
OK, U, F = "ok", 401, 403

PUBLIC = dict.fromkeys(CALLERS, OK)
ANY = {"anon": U, "operator": OK, "reviewer": OK, "admin": OK, "api_key": OK}
# The fixture video belongs to the operator, so the API key (an operator-like caller) gets 403.
ANY_OWNER = {**ANY, "api_key": F}
USER_ONLY = {**ANY, "api_key": F}
REVIEWER = {"anon": U, "operator": F, "reviewer": OK, "admin": OK, "api_key": F}
ADMIN = {"anon": U, "operator": F, "reviewer": F, "admin": OK, "api_key": F}

MATRIX: dict[tuple[str, str], dict[str, object]] = {
    ("GET", "/api/v1/health"): PUBLIC,
    ("POST", "/api/v1/auth/login"): PUBLIC,
    ("GET", "/api/v1/auth/me"): USER_ONLY,
    ("POST", "/api/v1/auth/change-password"): USER_ONLY,
    ("POST", "/api/v1/videos"): ANY,
    ("GET", "/api/v1/videos"): ANY,
    ("GET", "/api/v1/videos/{video_id}"): ANY_OWNER,
    ("GET", "/api/v1/videos/{video_id}/stream"): ANY_OWNER,
    ("POST", "/api/v1/videos/{video_id}/reanalyze"): REVIEWER,
    ("DELETE", "/api/v1/videos/{video_id}"): ADMIN,
    ("PUT", "/api/v1/videos/{video_id}/dispute"): REVIEWER,
    ("POST", "/api/v1/videos/{video_id}/reviews"): REVIEWER,
    ("GET", "/api/v1/review-queue"): REVIEWER,
    ("GET", "/api/v1/reports/summary"): REVIEWER,
    ("GET", "/api/v1/reports/export.csv"): REVIEWER,
    ("GET", "/api/v1/jobs/{job_id}"): ANY_OWNER,
    ("GET", "/api/v1/evidence/{evidence_id}"): ANY_OWNER,
    ("GET", "/api/v1/rubrics"): ANY,
    ("GET", "/api/v1/stations"): ANY,
    ("GET", "/api/v1/admin/users"): ADMIN,
    ("POST", "/api/v1/admin/users"): ADMIN,
    ("PATCH", "/api/v1/admin/users/{user_id}"): ADMIN,
    ("GET", "/api/v1/admin/warehouses"): ADMIN,
    ("POST", "/api/v1/admin/warehouses"): ADMIN,
    ("GET", "/api/v1/admin/stations"): ADMIN,
    ("POST", "/api/v1/admin/stations"): ADMIN,
    ("GET", "/api/v1/admin/api-keys"): ADMIN,
    ("POST", "/api/v1/admin/api-keys"): ADMIN,
    ("DELETE", "/api/v1/admin/api-keys/{key_id}"): ADMIN,
    ("GET", "/api/v1/admin/audit-log"): ADMIN,
}

BODIES = {
    ("POST", "/api/v1/auth/login"): {"email": "operator@m.test", "password": TEST_PASSWORD},
    ("POST", "/api/v1/auth/change-password"): {"current_password": "x", "new_password": "y"},
    ("POST", "/api/v1/admin/users"): {"email": "bad"},
    ("POST", "/api/v1/videos/{video_id}/reviews"): {"final_status": "pass"},
    ("PATCH", "/api/v1/admin/users/{user_id}"): {},
    ("PUT", "/api/v1/videos/{video_id}/dispute"): {"disputed": False},
    ("POST", "/api/v1/admin/warehouses"): {},
    ("POST", "/api/v1/admin/stations"): {},
    ("POST", "/api/v1/admin/api-keys"): {},
}


def test_matrix_covers_every_route(app):
    # FastAPI >= 0.14x keeps included routers nested, so read the routes from OpenAPI.
    routes = {
        (method.upper(), path) for path, ops in app.openapi()["paths"].items() for method in ops
    }
    assert routes == set(MATRIX)


@pytest.fixture
def world(app, make_user, make_api_key) -> dict:
    """An operator-owned video with a job, analysis, and evidence; one caller per kind."""
    operator = make_user(Role.operator, "operator@m.test")
    reviewer = make_user(Role.reviewer)
    admin = make_user(Role.admin)
    target = make_user(Role.operator)
    key_id, key_headers = make_api_key()
    with session_scope() as s:
        video = Video(
            original_filename="x.mp4",
            storage_key="videos/missing.mp4",
            process_type=ProcessType.Return,
            uploaded_by=operator.id,
            source=VideoSource.web,
        )
        s.add_all([video, Warehouse(code="W1", name="W1")])
        s.flush()
        job = Job(video_id=video.id)
        s.add(job)
        s.flush()
        analysis = Analysis(
            video_id=video.id,
            job_id=job.id,
            schema_version="1.0",
            engine_version="test",
            rubric_id="legacy-v1",
            total_score=50,
            confidence=0.5,
            status="review",
            decision="review",
            result_json={},
        )
        s.add(analysis)
        s.flush()
        ev = EvidenceItem(
            analysis_id=analysis.id, step_key="s", kind="frame", t_s=0, storage_key="e/x.jpg"
        )
        s.add(ev)
        s.flush()
        ids = {
            "video_id": video.id,
            "job_id": job.id,
            "evidence_id": ev.id,
            "user_id": target.id,
            "key_id": key_id,
        }
    headers = {
        "anon": {},
        "operator": auth(operator),
        "reviewer": auth(reviewer),
        "admin": auth(admin),
        "api_key": key_headers,
    }
    return {"ids": ids, "headers": headers}


@pytest.mark.parametrize("caller", CALLERS)
@pytest.mark.parametrize("route", list(MATRIX), ids=lambda r: f"{r[0]} {r[1]}")
def test_role_matrix(app, world, route, caller):
    method, path = route
    url = path.format(**world["ids"])
    with TestClient(app) as c:
        resp = c.request(method, url, headers=world["headers"][caller], json=BODIES.get(route))
    expected = MATRIX[route][caller]
    if expected == OK:
        assert resp.status_code not in (401, 403), resp.text
    else:
        assert resp.status_code == expected, resp.text
