from pathlib import Path

import pytest
from sqlalchemy import select

from tests.fixtures.video_factory import make_video
from vms.config import get_settings
from vms.db import session_scope
from vms.db.models import AuditLog, Job, JobStatus
from vms.services import jobs
from vms.storage import get_storage
from vms.worker import Worker, run_job


def _upload(client, path: Path, process_type: str = "Return", **data):
    with path.open("rb") as fh:
        return client.post(
            "/api/v1/videos",
            files={"file": (path.name, fh, "video/mp4")},
            data={"process_type": process_type, **data},
        )


def _stored(pattern: str) -> list[Path]:
    root = get_settings().data_dir
    return list(root.rglob(pattern)) if root.exists() else []


@pytest.fixture
def qr_video(tmp_path) -> Path:
    return make_video(tmp_path / "parcel.mp4", qr_text="AWB-777", text="LABEL")


def test_upload_worker_result_end_to_end(client, qr_video):
    resp = _upload(client, qr_video)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["duplicate"] is False
    assert body["job"]["status"] == "queued"
    assert body["video"]["final_status"] == "pending"
    video_id, job_id = body["video"]["id"], body["job"]["id"]

    assert Worker().run_once() is True
    assert Worker().run_once() is False  # queue drained

    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert (job["status"], job["progress"], job["error"]) == ("done", 1.0, None)

    detail = client.get(f"/api/v1/videos/{video_id}").json()
    analysis = detail["analysis"]
    assert analysis["result"]["schema_version"] == "2.0"
    assert analysis["result"]["barcodes"][0]["value"] == "AWB-777"
    assert detail["video"]["awb"] == "AWB-777"  # filled from the first barcode
    assert detail["video"]["final_status"] == analysis["status"]
    assert detail["video"]["latest_analysis"]["id"] == analysis["id"]
    assert detail["job"]["id"] == job_id
    assert analysis["evidence"], "expected at least one evidence frame"
    for ev in analysis["evidence"]:
        img = client.get(ev["url"])
        assert img.status_code == 200
        assert img.headers["content-type"] == "image/jpeg"
        assert img.content[:2] == b"\xff\xd8"

    with session_scope() as s:
        actions = set(s.scalars(select(AuditLog.action)))
    assert {"video.uploaded", "analysis.completed"} <= actions


def test_duplicate_upload_is_deduped(client, qr_video):
    first = _upload(client, qr_video).json()
    second = _upload(client, qr_video)
    assert second.status_code == 200
    assert second.json()["duplicate"] is True
    assert second.json()["video"]["id"] == first["video"]["id"]
    assert second.json()["job"]["id"] == first["job"]["id"]
    assert len(_stored("*.mp4")) == 1
    assert client.get("/api/v1/videos").json()["total"] == 1


def test_oversize_upload_returns_413(client, qr_video, monkeypatch):
    monkeypatch.setenv("VMS_MAX_UPLOAD_MB", "0")
    get_settings.cache_clear()
    resp = _upload(client, qr_video)
    assert resp.status_code == 413
    assert "detail" in resp.json()
    assert not _stored("*.mp4*")


def test_non_video_returns_400_and_is_not_kept(client, tmp_path):
    fake = tmp_path / "fake.mp4"
    fake.write_bytes(b"definitely not a video" * 100)
    resp = _upload(client, fake)
    assert resp.status_code == 400
    assert "not a readable video" in resp.json()["detail"]
    assert not _stored("*.mp4*")


def test_unsupported_extension_and_bad_process_type(client, tmp_path):
    txt = tmp_path / "notes.txt"
    txt.write_text("hello")
    assert _upload(client, txt).status_code == 400
    video = make_video(tmp_path / "v.mp4")
    assert _upload(client, video, process_type="Sideways").status_code == 422


def test_corrupt_stored_video_fails_job_with_message(client, qr_video):
    body = _upload(client, qr_video).json()
    _stored("*.mp4")[0].write_bytes(b"\x00" * 1024)  # file corrupted after upload
    Worker().run_once()
    job = client.get(f"/api/v1/jobs/{body['job']['id']}").json()
    assert job["status"] == "failed"
    assert job["error"]
    detail = client.get(f"/api/v1/videos/{body['video']['id']}").json()
    assert detail["analysis"] is None
    assert detail["video"]["final_status"] == "pending"


def test_shutdown_releases_job(client, qr_video):
    body = _upload(client, qr_video).json()
    with session_scope() as s:
        job = jobs.claim_next(s, "w-stop")
    status = run_job(job.id, "w-stop", get_storage(), get_settings(), stop=lambda: True)
    assert status == "released"
    with session_scope() as s:
        job = s.get(Job, body["job"]["id"])
        assert (job.status, job.attempts) == (JobStatus.queued, 0)
    assert not _stored("*.jpg")


def test_filters_and_pagination(client, tmp_path):
    for i, (pt, awb) in enumerate([("Return", "R-1"), ("Forward", "F-2"), ("Return", "R-3")]):
        video = make_video(tmp_path / f"clip{i}.mp4", qr_text=f"Q{i}", seconds=1)
        assert _upload(client, video, process_type=pt, awb=awb).status_code == 201

    def get(**params):
        resp = client.get("/api/v1/videos", params=params)
        assert resp.status_code == 200, resp.text
        return resp.json()

    page1 = get(page_size=2)
    assert (page1["total"], len(page1["items"]), page1["page"]) == (3, 2, 1)
    assert [v["awb"] for v in page1["items"]] == ["R-3", "F-2"]  # newest first
    assert [v["awb"] for v in get(page_size=2, page=2)["items"]] == ["R-1"]
    assert [v["awb"] for v in get(sort="created_at")["items"]] == ["R-1", "F-2", "R-3"]
    assert get(process_type="Forward")["total"] == 1
    assert get(awb="R-3")["items"][0]["original_filename"] == "clip2.mp4"
    assert get(q="CLIP1")["items"][0]["awb"] == "F-2"
    assert get(status="pending")["total"] == 3
    assert get(status="pass")["total"] == 0
    assert get(date_to="2000-01-01")["total"] == 0
    assert get(date_from="2000-01-01")["total"] == 3
    assert client.get("/api/v1/videos", params={"page_size": 500}).status_code == 422

    # Once analysed, q also matches decoded barcodes.
    while Worker().run_once():
        pass
    assert get(q="q0")["items"][0]["awb"] == "R-1"


def test_stream_supports_range(client, qr_video):
    video_id = _upload(client, qr_video).json()["video"]["id"]
    data = qr_video.read_bytes()
    full = client.get(f"/api/v1/videos/{video_id}/stream")
    assert full.status_code == 200
    assert full.content == data
    part = client.get(f"/api/v1/videos/{video_id}/stream", headers={"Range": "bytes=0-99"})
    assert part.status_code == 206
    assert part.headers["content-range"] == f"bytes 0-99/{len(data)}"
    assert part.content == data[:100]


def test_reanalyze_and_soft_delete(client, qr_video):
    video_id = _upload(client, qr_video).json()["video"]["id"]
    resp = client.post(f"/api/v1/videos/{video_id}/reanalyze")
    assert resp.status_code == 201
    assert resp.json()["status"] == "queued"
    assert client.delete(f"/api/v1/videos/{video_id}").status_code == 204
    assert client.get(f"/api/v1/videos/{video_id}").status_code == 404
    assert client.get("/api/v1/videos").json()["total"] == 0


def test_not_found_errors(client):
    for path in ("/api/v1/videos/999", "/api/v1/jobs/999", "/api/v1/evidence/999"):
        resp = client.get(path)
        assert resp.status_code == 404
        assert "detail" in resp.json()


def test_rubrics(client):
    rubrics = {r["process_type"]: r for r in client.get("/api/v1/rubrics").json()}
    assert set(rubrics) == {"Forward", "Return"}
    assert sum(s["weight"] for s in rubrics["Return"]["steps"]) == 100


def test_openapi_lists_phase2_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    for p in (
        "/api/v1/health",
        "/api/v1/videos",
        "/api/v1/videos/{video_id}",
        "/api/v1/videos/{video_id}/stream",
        "/api/v1/videos/{video_id}/reanalyze",
        "/api/v1/jobs/{job_id}",
        "/api/v1/evidence/{evidence_id}",
        "/api/v1/rubrics",
    ):
        assert p in paths, p


def test_stations_and_uploader_name_for_any_user(client, qr_video):
    body = _upload(client, qr_video).json()
    assert body["video"]["uploaded_by_name"]
    listed = client.get("/api/v1/videos").json()["items"][0]
    assert listed["uploaded_by_name"] == body["video"]["uploaded_by_name"]
    assert client.get("/api/v1/stations").json() == []
