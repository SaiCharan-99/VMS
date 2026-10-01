from collections.abc import Iterator
from pathlib import Path

import pytest

from vms.analysis.detectors import get_ocr_reader, get_yolo
from vms.config import get_settings


def _clear_caches() -> None:
    get_settings.cache_clear()
    get_ocr_reader.cache_clear()
    get_yolo.cache_clear()


@pytest.fixture(autouse=True)
def isolated_settings(
    request: pytest.FixtureRequest, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[None]:
    """Keep tests off the real DB/data dir; disable heavy models unless marked `models`."""
    monkeypatch.setenv("VMS_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("VMS_DB_URL", f"sqlite:///{(tmp_path / 'results.db').as_posix()}")
    if request.node.get_closest_marker("models") is None:
        monkeypatch.setenv("VMS_OCR_ENABLED", "false")
        monkeypatch.setenv("VMS_YOLO_ENABLED", "false")
    _clear_caches()
    yield
    _clear_caches()
