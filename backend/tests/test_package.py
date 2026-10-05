import subprocess
import sys

from vms.analysis.detectors import get_ocr_reader, get_yolo
from vms.config import get_settings

IMPORT_CHECK = """
import sys
import vms, vms.analysis, vms.api.main, vms.cli
print(",".join(m for m in ("easyocr", "ultralytics", "torch") if m in sys.modules))
"""


def test_importing_vms_does_not_load_heavy_models():
    out = subprocess.run(
        [sys.executable, "-c", IMPORT_CHECK], capture_output=True, text=True, check=True
    )
    assert out.stdout.strip() == ""


def test_settings_env_override(monkeypatch):
    monkeypatch.setenv("VMS_PROCESS_FPS", "7")
    monkeypatch.setenv("VMS_BLUR_THRESHOLD", "12.5")
    get_settings.cache_clear()
    settings = get_settings()
    assert settings.process_fps == 7
    assert settings.blur_threshold == 12.5


def test_detectors_disabled_return_none():
    assert get_ocr_reader() is None
    assert get_yolo() is None
