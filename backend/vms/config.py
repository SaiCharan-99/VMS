from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VMS_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    # Legacy results store; kept at the repo root until Phase 2 imports it.
    db_url: str = "sqlite:///audit_results.db"
    yolo_weights: Path = Path("yolov8n.pt")
    ocr_enabled: bool = True
    yolo_enabled: bool = True
    process_fps: int = 3
    blur_threshold: float = 30.0
    max_upload_mb: int = 500

    @property
    def sqlite_path(self) -> Path:
        prefix = "sqlite:///"
        if not self.db_url.startswith(prefix):
            raise ValueError(f"Legacy store needs a sqlite:/// URL, got {self.db_url!r}")
        return Path(self.db_url[len(prefix) :])


@lru_cache
def get_settings() -> Settings:
    return Settings()
