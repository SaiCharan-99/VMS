"""Retention purge (files go, rows stay) and the dispute flag that blocks it."""

import io
from datetime import timedelta

import pytest
from sqlalchemy import select

from tests.conftest import auth
from vms import cli
from vms.db import session_scope
from vms.db.models import (
    AuditLog,
    FinalStatus,
    Job,
    JobStatus,
    ProcessType,
    Role,
    Video,
    VideoSource,
    utcnow,
)
from vms.services.retention import purge
from vms.storage import get_storage


def _video(age_days: int, status: FinalStatus, **kw) -> int:
    storage = get_storage()
    with session_scope() as s:
        video = Video(
            original_filename="v.mp4",
            process_type=ProcessType.Return,
            source=VideoSource.web,
            final_status=status,
            created_at=utcnow() - timedelta(days=age_days),
            size_bytes=4,
            **kw,
        )
        s.add(video)
        s.flush()
        video.storage_key = f"videos/test/{video.id}.mp4"
        storage.save_stream(video.storage_key, io.BytesIO(b"data"))
        return video.id


def _file_exists(video_id: int) -> bool:
    with session_scope() as s:
        return get_storage().exists(s.get(Video, video_id).storage_key)


def test_purge_keeps_open_disputed_recent_and_busy_videos(db_ready):
    old_pass = _video(200, FinalStatus.pass_)
    old_fail = _video(200, FinalStatus.fail)
    recent = _video(10, FinalStatus.pass_)
    awaiting_review = _video(200, FinalStatus.review)
    pending = _video(200, FinalStatus.pending)
    disputed = _video(200, FinalStatus.fail, disputed_at=utcnow())
    busy = _video(200, FinalStatus.pass_)
    with session_scope() as s:
        s.add(Job(video_id=busy, status=JobStatus.queued))

    with session_scope() as s:
        dry = purge(s, get_storage(), 180, dry_run=True)
    assert dry.video_ids == [old_pass, old_fail]
    assert _file_exists(old_pass)  # dry run deletes nothing

    with session_scope() as s:
        report = purge(s, get_storage(), 180)
    assert (report.purged, report.bytes_freed) == (2, 8)
    for kept in (recent, awaiting_review, pending, disputed, busy):
        assert _file_exists(kept)
    with session_scope() as s:
        for vid in (old_pass, old_fail):
            video = s.get(Video, vid)
            assert video.file_purged_at is not None and video.deleted_at is None
            assert not get_storage().exists(video.storage_key)
        logged = s.scalars(select(AuditLog.entity_id).where(AuditLog.action == "video.file_purged"))
        assert sorted(logged) == sorted([str(old_pass), str(old_fail)])
        assert purge(s, get_storage(), 180).purged == 0  # idempotent


def test_purge_rejects_zero_days(db_ready):
    with session_scope() as s, pytest.raises(ValueError):
        purge(s, get_storage(), 0)


def test_purged_video_api(client, db_ready):
    vid = _video(200, FinalStatus.pass_)
    with session_scope() as s:
        purge(s, get_storage(), 30)
    body = client.get(f"/api/v1/videos/{vid}").json()["video"]
    assert body["file_purged"] is True and body["stream_url"] is None
    assert client.get(f"/api/v1/videos/{vid}/stream").status_code == 410
    assert client.post(f"/api/v1/videos/{vid}/reanalyze").status_code == 409


def test_dispute_flag_round_trip_and_audit(app, make_user, anon_client):
    reviewer = make_user(Role.reviewer)
    vid = _video(200, FinalStatus.fail)
    headers = auth(reviewer)
    resp = anon_client.put(
        f"/api/v1/videos/{vid}/dispute", json={"disputed": True}, headers=headers
    )
    assert resp.status_code == 200 and resp.json()["disputed"] is True
    with session_scope() as s:
        assert purge(s, get_storage(), 30).purged == 0
    anon_client.put(f"/api/v1/videos/{vid}/dispute", json={"disputed": False}, headers=headers)
    with session_scope() as s:
        actions = list(s.scalars(select(AuditLog.action).where(AuditLog.entity_id == str(vid))))
        assert actions == ["video.dispute_opened", "video.dispute_closed"]
        assert all(
            a.actor_user_id == reviewer.id
            for a in s.scalars(select(AuditLog).where(AuditLog.entity_id == str(vid)))
        )


def test_cli_purge_needs_days(db_ready, monkeypatch, capsys):
    assert cli.main(["purge"]) == 1
    _video(200, FinalStatus.pass_)
    monkeypatch.setenv("VMS_RETENTION_DAYS", "90")
    from vms.config import get_settings

    get_settings.cache_clear()
    assert cli.main(["purge", "--dry-run"]) == 0
    assert "Would delete 1 video files older than 90 days" in capsys.readouterr().out
