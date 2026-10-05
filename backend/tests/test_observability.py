"""Health, metrics, request ids, JSON logs, and production config guards."""

import json
import logging

import pytest
from fastapi.testclient import TestClient

from tests.fixtures.video_factory import make_video
from vms.api.routers import health as health_router
from vms.config import get_settings
from vms.logging import JsonFormatter, _ContextFilter, bind_log_context, clear_log_context
from vms.metrics import WORKER_REGISTRY
from vms.security import InsecureConfigError
from vms.worker import Worker


def test_health_reports_db_storage_and_detectors(anon_client):
    resp = anon_client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert (body["status"], body["db"], body["storage"]) == ("ok", "ok", "ok")
    assert body["detectors"]["ocr"] is False  # disabled in tests
    assert not list(get_settings().data_dir.glob(".health-*"))  # probe file cleaned up


def test_health_is_503_when_storage_is_not_writable(anon_client, monkeypatch):
    monkeypatch.setattr(health_router, "_storage_state", lambda: "error: PermissionError")
    resp = anon_client.get("/api/v1/health")
    assert resp.status_code == 503
    assert resp.json()["status"] == "degraded"


def test_request_id_is_echoed_or_generated(anon_client):
    resp = anon_client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert resp.headers["X-Request-ID"] == "abc-123"
    generated = anon_client.get("/api/v1/health", headers={"X-Request-ID": "bad id\n"})
    assert len(generated.headers["X-Request-ID"]) == 32


def test_metrics_expose_latency_and_queue_gauges(client, tmp_path):
    video = make_video(tmp_path / "v.mp4", qr_text="AWB-1")
    with video.open("rb") as fh:
        client.post(
            "/api/v1/videos",
            files={"file": ("v.mp4", fh, "video/mp4")},
            data={"process_type": "Return"},
        )
    text = client.get("/metrics").text
    assert 'vms_jobs{status="queued"} 1.0' in text
    assert 'route="/api/v1/videos"' in text
    assert "/metrics" not in client.get("/openapi.json").json()["paths"]


def _analyses_timed() -> float:
    return sum(
        m.value
        for m in WORKER_REGISTRY.collect()
        for m in m.samples
        if m.name == "vms_analysis_duration_seconds_count"
    )


def test_worker_records_analysis_duration(client, tmp_path):
    before = _analyses_timed()
    video = make_video(tmp_path / "v.mp4", qr_text="AWB-1")
    with video.open("rb") as fh:
        client.post(
            "/api/v1/videos",
            files={"file": ("v.mp4", fh, "video/mp4")},
            data={"process_type": "Return"},
        )
    assert Worker().run_once()
    assert _analyses_timed() == before + 1
    assert "vms_analysis_duration" not in client.get("/metrics").text  # worker-only metric


def test_json_log_lines_carry_context_ids():
    record = logging.makeLogRecord({"msg": "hello %s", "args": ("x",), "levelname": "INFO"})
    bind_log_context(request_id="r1", user_id=7)
    try:
        _ContextFilter().filter(record)
    finally:
        clear_log_context()
    line = json.loads(JsonFormatter().format(record))
    assert line["msg"] == "hello x"
    assert (line["request_id"], line["user_id"]) == ("r1", 7)


def test_request_log_line_has_user_id(client, caplog):
    with caplog.at_level(logging.INFO, logger="vms.request"):
        client.get("/api/v1/auth/me")
    (record,) = [r for r in caplog.records if r.name == "vms.request"]
    assert record.user_id is not None and record.request_id
    assert record.status == 200


@pytest.mark.parametrize(
    ("env", "origins", "ok"),
    [("dev", '["*"]', True), ("prod", '["*"]', False), ("prod", '["https://vms.example"]', True)],
)
def test_wildcard_cors_rejected_outside_dev(monkeypatch, db_ready, env, origins, ok):
    from vms import security
    from vms.api.main import create_app

    monkeypatch.setenv("VMS_ENV", env)
    monkeypatch.setenv("VMS_CORS_ORIGINS", origins)
    get_settings.cache_clear()
    security.jwt_secret.cache_clear()
    if ok:
        create_app()
    else:
        with pytest.raises(InsecureConfigError):
            create_app()


def test_cors_only_answers_configured_origins(app):
    with TestClient(app) as c:
        allowed = c.options(
            "/api/v1/health",
            headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
        )
        denied = c.options(
            "/api/v1/health",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
        )
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "access-control-allow-origin" not in denied.headers


def test_worker_heartbeat_file(db_ready, tmp_path, monkeypatch):
    import threading
    import time

    beat = tmp_path / "worker.alive"
    monkeypatch.setenv("VMS_WORKER_HEARTBEAT_FILE", str(beat))
    get_settings.cache_clear()
    worker = Worker()
    thread = threading.Thread(target=worker.run, args=(0.1,), daemon=True)
    thread.start()
    deadline = time.monotonic() + 5
    while not beat.exists() and time.monotonic() < deadline:
        time.sleep(0.05)
    worker.request_stop()
    thread.join(5)
    assert beat.exists()
