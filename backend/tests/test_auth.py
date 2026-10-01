"""Login, tokens, API keys, operator isolation, admin CRUD, audit rows, and the auth CLI."""

from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.conftest import TEST_PASSWORD, auth
from tests.fixtures.video_factory import make_video
from vms import security
from vms.cli import main as cli_main
from vms.db import session_scope
from vms.db.models import AuditLog, Role, User, Video


def _login(c: TestClient, email: str, password: str = TEST_PASSWORD):
    return c.post("/api/v1/auth/login", json={"email": email, "password": password})


def _actions() -> list[str]:
    with session_scope() as s:
        return list(s.scalars(select(AuditLog.action).order_by(AuditLog.id)))


def _upload(c: TestClient, path, **headers):
    with path.open("rb") as fh:
        return c.post(
            "/api/v1/videos",
            files={"file": (path.name, fh, "video/mp4")},
            data={"process_type": "Return"},
            headers=headers,
        )


# --- login & tokens --------------------------------------------------------------------------


def test_login_me_and_audit(anon_client, make_user):
    user = make_user(Role.reviewer, "Rita@Test.local")
    resp = _login(anon_client, "  rita@test.LOCAL ")  # emails are case-insensitive
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["token_type"] == "bearer" and body["user"]["role"] == "reviewer"
    me = anon_client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    ).json()
    assert me["id"] == user.id and me["last_login_at"] is not None
    assert _actions()[-1] == "auth.login"


def test_bad_login_is_401_and_audited(anon_client, make_user):
    make_user(Role.operator, "op@test.local")
    assert _login(anon_client, "op@test.local", "wrong-password").status_code == 401
    assert _login(anon_client, "nobody@test.local").status_code == 401
    with session_scope() as s:
        rows = s.scalars(select(AuditLog).where(AuditLog.action == "auth.login_failed")).all()
        assert [r.data["email"] for r in rows] == ["op@test.local", "nobody@test.local"]


@pytest.mark.parametrize(
    "token",
    [
        "not-a-jwt",
        jwt.encode(
            {"sub": "1", "exp": 9999999999}, "another-secret-" + "y" * 32, algorithm="HS256"
        ),
    ],
)
def test_invalid_tokens_are_401(anon_client, token):
    resp = anon_client.get("/api/v1/videos", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_expired_token_is_401(anon_client, make_user):
    user = make_user()
    token = security.create_access_token(user.id, ttl=timedelta(seconds=-1))
    resp = anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401


def test_inactive_user_cannot_login_or_use_token(client, anon_client, make_user):
    user = make_user()
    headers = auth(user)
    resp = client.patch(f"/api/v1/admin/users/{user.id}", json={"is_active": False})
    assert resp.status_code == 200 and resp.json()["is_active"] is False
    assert anon_client.get("/api/v1/auth/me", headers=headers).status_code == 401
    assert _login(anon_client, user.email).status_code == 401
    assert "user.deactivated" in _actions()


def test_login_rate_limit(anon_client, make_user):
    make_user(Role.operator, "op@test.local")
    for _ in range(10):
        assert _login(anon_client, "op@test.local", "wrong-password").status_code == 401
    assert _login(anon_client, "op@test.local").status_code == 429  # even the right password
    assert _login(anon_client, "OP@test.local").status_code == 429  # same normalized email
    make_user(Role.operator, "other@test.local")
    assert _login(anon_client, "other@test.local").status_code == 200


def test_change_password(anon_client, make_user):
    user = make_user()
    h = auth(user)
    url = "/api/v1/auth/change-password"
    wrong = {"current_password": "nope", "new_password": "new-password-1"}
    assert anon_client.post(url, json=wrong, headers=h).status_code == 400
    short = {"current_password": TEST_PASSWORD, "new_password": "short"}
    assert anon_client.post(url, json=short, headers=h).status_code == 422
    ok = {"current_password": TEST_PASSWORD, "new_password": "new-password-1"}
    assert anon_client.post(url, json=ok, headers=h).status_code == 204
    assert _login(anon_client, user.email).status_code == 401
    assert _login(anon_client, user.email, "new-password-1").status_code == 200
    assert "user.password_changed" in _actions()


def test_jwt_secret_required_outside_dev(monkeypatch):
    from vms.api.main import create_app
    from vms.config import get_settings

    monkeypatch.setenv("VMS_ENV", "prod")
    monkeypatch.delenv("VMS_JWT_SECRET")
    get_settings.cache_clear()
    security.jwt_secret.cache_clear()
    with pytest.raises(security.InsecureConfigError):
        create_app()


def test_system_user_cannot_log_in(anon_client):
    assert _login(anon_client, "system@vms.local", "").status_code == 422
    assert _login(anon_client, "system@vms.local", "anything").status_code == 401


# --- visibility ------------------------------------------------------------------------------


def test_operator_isolation(app, client, make_user, tmp_path):
    alice, bob = make_user(Role.operator), make_user(Role.operator)
    reviewer = make_user(Role.reviewer)
    with TestClient(app) as c:
        a = _upload(c, make_video(tmp_path / "a.mp4", qr_text="A"), **auth(alice)).json()
        _upload(c, make_video(tmp_path / "b.mp4", qr_text="B"), **auth(bob))
        vid, job = a["video"]["id"], a["job"]["id"]

        assert c.get("/api/v1/videos", headers=auth(alice)).json()["total"] == 1
        bob_list = c.get("/api/v1/videos", headers=auth(bob)).json()
        assert [v["original_filename"] for v in bob_list["items"]] == ["b.mp4"]
        # The uploaded_by filter can't widen an operator's view.
        params = {"uploaded_by": alice.id}
        assert c.get("/api/v1/videos", params=params, headers=auth(bob)).json()["total"] == 0
        for path in (
            f"/api/v1/videos/{vid}",
            f"/api/v1/videos/{vid}/stream",
            f"/api/v1/jobs/{job}",
        ):
            assert c.get(path, headers=auth(bob)).status_code == 403, path
            assert c.get(path, headers=auth(alice)).status_code == 200, path
            assert c.get(path, headers=auth(reviewer)).status_code == 200, path
        assert c.get("/api/v1/videos", headers=auth(reviewer)).json()["total"] == 2
    assert client.get("/api/v1/videos").json()["total"] == 2


# --- API keys --------------------------------------------------------------------------------


def test_api_key_flow_and_revocation(app, client, anon_client, tmp_path):
    created = client.post("/api/v1/admin/api-keys", json={"name": "WMS integration"})
    assert created.status_code == 201
    key = created.json()["key"]
    assert key.startswith("vms_")
    listed = client.get("/api/v1/admin/api-keys").json()
    assert "key" not in listed[0] and key not in str(listed)
    with session_scope() as s:  # only the hash is stored
        assert key not in str(s.execute(select(User)).all())

    h = {"X-API-Key": key}
    resp = _upload(anon_client, make_video(tmp_path / "k.mp4", qr_text="K"), **h)
    assert resp.status_code == 201, resp.text
    assert resp.json()["video"]["source"] == "api"
    assert anon_client.get("/api/v1/videos", headers=h).json()["total"] == 1
    assert anon_client.get("/api/v1/auth/me", headers=h).status_code == 403
    with session_scope() as s:
        upload = s.scalar(select(AuditLog).where(AuditLog.action == "video.uploaded"))
        assert upload.actor_api_key_id == created.json()["id"] and upload.actor_user_id is None

    assert client.delete(f"/api/v1/admin/api-keys/{created.json()['id']}").status_code == 204
    assert anon_client.get("/api/v1/videos", headers=h).status_code == 401
    assert client.get("/api/v1/admin/api-keys").json()[0]["revoked_at"] is not None
    assert anon_client.get("/api/v1/videos", headers={"X-API-Key": "vms_bogus"}).status_code == 401
    assert {"api_key.created", "api_key.revoked"} <= set(_actions())


# --- admin CRUD ------------------------------------------------------------------------------


def test_admin_user_crud(client):
    body = {
        "email": "new@test.local",
        "name": "New",
        "password": "long-enough-1",
        "role": "operator",
    }
    resp = client.post("/api/v1/admin/users", json=body)
    assert resp.status_code == 201, resp.text
    uid = resp.json()["id"]
    assert client.post("/api/v1/admin/users", json=body).status_code == 409
    assert (
        client.post(
            "/api/v1/admin/users", json={**body, "email": "x@t.l", "password": "short"}
        ).status_code
        == 422
    )
    bad_wh = {**body, "email": "y@t.l", "warehouse_id": 999}
    assert client.post("/api/v1/admin/users", json=bad_wh).status_code == 400

    resp = client.patch(f"/api/v1/admin/users/{uid}", json={"role": "reviewer", "name": "Renamed"})
    assert resp.json()["role"] == "reviewer" and resp.json()["name"] == "Renamed"
    assert client.patch("/api/v1/admin/users/9999", json={}).status_code == 404

    page = client.get("/api/v1/admin/users", params={"role": "reviewer"}).json()
    assert [u["email"] for u in page["items"]] == ["new@test.local"]


def test_admin_cannot_lock_themselves_out(client):
    me = client.get("/api/v1/auth/me").json()
    for change in ({"role": "operator"}, {"is_active": False}):
        assert client.patch(f"/api/v1/admin/users/{me['id']}", json=change).status_code == 400


def test_warehouses_and_stations(client):
    wh = client.post("/api/v1/admin/warehouses", json={"code": "BLR", "name": "Bengaluru"})
    assert wh.status_code == 201
    assert (
        client.post("/api/v1/admin/warehouses", json={"code": "BLR", "name": "x"}).status_code
        == 409
    )
    wid = wh.json()["id"]
    st = {"warehouse_id": wid, "code": "S1", "name": "Station 1"}
    assert client.post("/api/v1/admin/stations", json=st).status_code == 201
    assert client.post("/api/v1/admin/stations", json=st).status_code == 409
    missing_wh = {**st, "warehouse_id": 999}
    assert client.post("/api/v1/admin/stations", json=missing_wh).status_code == 400
    assert len(client.get("/api/v1/admin/stations", params={"warehouse_id": wid}).json()) == 1
    assert [w["code"] for w in client.get("/api/v1/admin/warehouses").json()] == ["BLR"]
    assert {"warehouse.created", "station.created"} <= set(_actions())


def test_upload_rejects_unknown_station(client, tmp_path):
    path = make_video(tmp_path / "s.mp4")
    with path.open("rb") as fh:
        resp = client.post(
            "/api/v1/videos",
            files={"file": ("s.mp4", fh, "video/mp4")},
            data={"process_type": "Return", "station_id": "42"},
        )
    assert resp.status_code == 400


def test_audit_log_endpoint_filters_and_pages(client, make_user):
    for i in range(3):
        client.post("/api/v1/admin/warehouses", json={"code": f"W{i}", "name": "W"})
    page = client.get("/api/v1/admin/audit-log", params={"action": "warehouse.", "page_size": 2})
    body = page.json()
    assert body["total"] == 3 and len(body["items"]) == 2
    assert body["items"][0]["data"]["code"] == "W2"  # newest first
    admin_id = client.get("/api/v1/auth/me").json()["id"]
    assert all(item["actor_user_id"] == admin_id for item in body["items"])
    by_entity = client.get(
        "/api/v1/admin/audit-log", params={"entity_type": "warehouse", "entity_id": "1"}
    ).json()
    assert by_entity["total"] == 1


def test_video_actions_are_audited_with_actor(client, tmp_path):
    vid = _upload(client, make_video(tmp_path / "v.mp4")).json()["video"]["id"]
    client.post(f"/api/v1/videos/{vid}/reanalyze")
    client.delete(f"/api/v1/videos/{vid}")
    admin_id = client.get("/api/v1/auth/me").json()["id"]
    with session_scope() as s:
        rows = s.scalars(select(AuditLog).where(AuditLog.entity_type == "video")).all()
        assert [r.action for r in rows] == ["video.uploaded", "video.reanalyze", "video.deleted"]
        assert {r.actor_user_id for r in rows} == {admin_id}
        assert s.get(Video, vid).uploaded_by == admin_id


def test_password_never_returned(client, anon_client, make_user):
    user = make_user(Role.operator, "p@test.local")
    responses = [
        _login(anon_client, "p@test.local"),
        client.get("/api/v1/auth/me"),
        client.get("/api/v1/admin/users"),
        client.patch(f"/api/v1/admin/users/{user.id}", json={"password": "reset-password-1"}),
        client.post(
            "/api/v1/admin/users",
            json={"email": "q@t.l", "name": "Q", "password": "secret-pass-9", "role": "admin"},
        ),
        client.get("/api/v1/admin/audit-log"),
    ]
    for resp in responses:
        assert resp.status_code in (200, 201), resp.text
        text = resp.text
        assert "password_hash" not in text and "$argon2" not in text
        assert TEST_PASSWORD not in text and "reset-password-1" not in text
        assert "secret-pass-9" not in text


# --- CLI -------------------------------------------------------------------------------------


def test_create_admin_cli_then_login(anon_client, monkeypatch, capsys):
    monkeypatch.setattr("getpass.getpass", lambda prompt="": "cli-admin-pass-1")
    assert cli_main(["create-admin", "--email", "Boss@Test.local", "--name", "Boss"]) == 0
    assert cli_main(["create-admin", "--email", "boss@test.local", "--name", "Boss"]) == 1
    token = _login(anon_client, "boss@test.local", "cli-admin-pass-1").json()["access_token"]
    me = anon_client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert (me["email"], me["role"]) == ("boss@test.local", "admin")


def test_create_admin_cli_mismatched_password(db_ready, monkeypatch):
    answers = iter(["first-password-1", "second-password-1"])
    monkeypatch.setattr("getpass.getpass", lambda prompt="": next(answers))
    assert cli_main(["create-admin", "--email", "a@test.local", "--name", "A"]) == 1


def test_seed_demo(anon_client, monkeypatch, capsys):
    from vms.services.demo import DEMO_USERS

    assert cli_main(["seed-demo"]) == 0
    assert "operator@vms.local" in capsys.readouterr().out
    assert cli_main(["seed-demo"]) == 0  # idempotent
    for email, _name, role, password in DEMO_USERS:
        resp = _login(anon_client, email, password)
        assert resp.status_code == 200 and resp.json()["user"]["role"] == role.value
    with session_scope() as s:
        assert s.scalar(select(User).where(User.email == "admin@vms.local")).warehouse_id


def test_seed_demo_refuses_outside_dev(db_ready, monkeypatch):
    from vms.config import get_settings

    monkeypatch.setenv("VMS_ENV", "prod")
    get_settings.cache_clear()
    assert cli_main(["seed-demo"]) == 1
