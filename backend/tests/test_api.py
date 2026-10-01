"""Legacy v1 compatibility routes (`/health`, `/analyze`, `/results`)."""

import json

from tests.fixtures.video_factory import make_video


def test_health(anon_client):
    for path in ("/health", "/api/v1/health"):
        body = anon_client.get(path).json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"
        assert body["detectors"]["ocr"] is False  # disabled in tests


def test_analyze_happy_path_and_results(api_client, tmp_path):
    video = make_video(tmp_path / "v.mp4", qr_text="AWB-1", text="LABEL")
    with video.open("rb") as fh:
        resp = api_client.post(
            "/analyze",
            files={"file": ("v.mp4", fh, "video/mp4")},
            data={"process_type": "Forward"},
        )
    assert resp.status_code == 200, resp.text
    result = resp.json()["result"]
    assert result["detected_barcode"] == "AWB-1"
    assert {"direction_changes", "estimated_sides"} <= result["metrics"].keys()
    assert set(result["scores"]) == {"shipping_label", "unboxing", "tags", "product"}

    rows = api_client.get("/results").json()["results"]
    assert rows[0]["id"] == result["record_id"]
    assert rows[0]["file_name"] == "v.mp4"
    assert json.loads(rows[0]["result_json"])["detected_barcode"] == "AWB-1"

    # The sync analysis is stored in the new tables too.
    page = api_client.get("/api/v1/videos").json()
    assert page["total"] == 1
    assert page["items"][0]["source"] == "api"
    assert page["items"][0]["awb"] == "AWB-1"


def test_corrupt_file_returns_400(api_client):
    resp = api_client.post("/analyze", files={"file": ("bad.mp4", b"not a video", "video/mp4")})
    assert resp.status_code == 400
    assert "detail" in resp.json()


def test_unsupported_extension_returns_400(api_client):
    resp = api_client.post("/analyze", files={"file": ("x.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_bad_process_type_returns_400(api_client):
    resp = api_client.post(
        "/analyze",
        files={"file": ("v.mp4", b"x", "video/mp4")},
        data={"process_type": "Sideways"},
    )
    assert resp.status_code == 400
