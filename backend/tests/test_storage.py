import io

import pytest

from vms.storage import LocalStorage, TooLargeError


def test_round_trip(tmp_path):
    storage = LocalStorage(tmp_path)
    data = b"x" * (3 * 1024 * 1024 + 7)
    size, sha = storage.save_stream("videos/2026/10/a.mp4", io.BytesIO(data))
    assert size == len(data)
    assert len(sha) == 64
    assert storage.exists("videos/2026/10/a.mp4")
    with storage.open("videos/2026/10/a.mp4") as fh:
        assert fh.read() == data
    assert storage.path("videos/2026/10/a.mp4") == tmp_path / "videos" / "2026" / "10" / "a.mp4"
    storage.delete("videos/2026/10/a.mp4")
    assert not storage.exists("videos/2026/10/a.mp4")


def test_too_large_leaves_nothing_behind(tmp_path):
    storage = LocalStorage(tmp_path)
    with pytest.raises(TooLargeError):
        storage.save_stream("v/a.mp4", io.BytesIO(b"x" * 100), max_bytes=10)
    assert list((tmp_path / "v").iterdir()) == []


@pytest.mark.parametrize("key", ["../x", "/abs", "a/../../b", ""])
def test_rejects_escaping_keys(tmp_path, key):
    with pytest.raises(ValueError):
        LocalStorage(tmp_path).path(key)


def test_delete_directory(tmp_path):
    storage = LocalStorage(tmp_path)
    storage.save_stream("evidence/abc/s_0.jpg", io.BytesIO(b"j"))
    storage.delete("evidence/abc")
    assert not storage.exists("evidence/abc")
