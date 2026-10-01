import pytest
from fastapi.testclient import TestClient

from tests.fixtures.video_factory import make_video
from vms.api.main import app, get_store
from vms.legacy_store import AuditStore


@pytest.fixture
def client(tmp_path):
    store = AuditStore(tmp_path / "api.db")
    app.dependency_overrides[get_store] = lambda: store
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_analyze_happy_path_and_results(client, tmp_path):
    video = make_video(tmp_path / "v.mp4", qr_text="AWB-1", text="LABEL")
    with video.open("rb") as fh:
        resp = client.post(
            "/analyze",
            files={"file": ("v.mp4", fh, "video/mp4")},
            data={"process_type": "Forward"},
        )
    assert resp.status_code == 200, resp.text
    result = resp.json()["result"]
    assert result["detected_barcode"] == "AWB-1"
    assert {"direction_changes", "estimated_sides"} <= result["metrics"].keys()
    assert set(result["scores"]) == {"shipping_label", "unboxing", "tags", "product"}

    rows = client.get("/results").json()["results"]
    assert rows[0]["id"] == result["record_id"]


def test_corrupt_file_returns_400(client):
    resp = client.post("/analyze", files={"file": ("bad.mp4", b"not a video", "video/mp4")})
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_unsupported_extension_returns_400(client):
    resp = client.post("/analyze", files={"file": ("x.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_bad_process_type_returns_400(client):
    resp = client.post(
        "/analyze",
        files={"file": ("v.mp4", b"x", "video/mp4")},
        data={"process_type": "Sideways"},
    )
    assert resp.status_code == 400
