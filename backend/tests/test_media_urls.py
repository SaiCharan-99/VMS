"""Signed stream/evidence URLs: `<video>`/`<img>` tags can't send an Authorization header."""

from tests.fixtures.video_factory import make_video
from tests.test_api_v1 import _upload
from vms.security import sign_media_url
from vms.worker import Worker


def _analyzed(client, tmp_path) -> dict:
    video = make_video(tmp_path / "parcel.mp4", qr_text="AWB-1", text="LABEL")
    video_id = _upload(client, video).json()["video"]["id"]
    Worker().run_once()
    return client.get(f"/api/v1/videos/{video_id}").json()


def test_signed_urls_work_without_credentials(client, anon_client, tmp_path):
    detail = _analyzed(client, tmp_path)
    stream_url = detail["video"]["stream_url"]
    assert "sig=" in stream_url and "exp=" in stream_url
    resp = anon_client.get(stream_url, headers={"Range": "bytes=0-99"})
    assert resp.status_code == 206
    ev_url = detail["analysis"]["evidence"][0]["url"]
    assert anon_client.get(ev_url).status_code == 200


def test_bad_or_expired_or_foreign_signature_needs_credentials(client, anon_client, tmp_path):
    detail = _analyzed(client, tmp_path)
    video_id = detail["video"]["id"]
    path = f"/api/v1/videos/{video_id}/stream"
    tampered = detail["video"]["stream_url"][:-4] + "0000"
    expired = sign_media_url(path, ttl_s=-10)
    # A signature for one path doesn't open another.
    foreign = sign_media_url("/api/v1/videos/999/stream").replace("/999/", f"/{video_id}/")
    for url in (path, tampered, expired, foreign):
        assert anon_client.get(url).status_code == 401, url
    # Normal bearer auth still works without a signature.
    assert client.get(path, headers={"Range": "bytes=0-9"}).status_code == 206
