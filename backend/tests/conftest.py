from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from vms.analysis.detectors import get_ocr_reader, get_yolo
from vms.config import get_settings
from vms.db import create_all, get_engine, get_sessionmaker


def _clear_caches() -> None:
    if get_engine.cache_info().currsize:
        get_engine().dispose()  # release the SQLite file so tmp_path can be removed
    get_settings.cache_clear()
    get_ocr_reader.cache_clear()
    get_yolo.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()


@pytest.fixture(autouse=True)
def isolated_settings(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Keep tests off the real DB/data dir; disable heavy models unless marked `models`."""
    monkeypatch.setenv("VMS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VMS_DB_URL", f"sqlite:///{(tmp_path / 'vms.db').as_posix()}")
    if request.node.get_closest_marker("models") is None:
        monkeypatch.setenv("VMS_OCR_ENABLED", "false")
        monkeypatch.setenv("VMS_YOLO_ENABLED", "false")
    _clear_caches()
    yield
    _clear_caches()


@pytest.fixture
def db_ready() -> None:
    """Tables + seeded system user in the per-test SQLite DB."""
    create_all()


@pytest.fixture
def client(db_ready: None) -> Iterator[TestClient]:
    from vms.api.main import create_app

    with TestClient(create_app()) as c:
        yield c
