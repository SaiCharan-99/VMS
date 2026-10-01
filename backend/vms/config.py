from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="VMS_", env_file=".env", extra="ignore")

    data_dir: Path = Path("data")
    db_url: str = "sqlite:///data/vms.db"
    yolo_weights: Path = Path("yolov8n.pt")
    ocr_enabled: bool = True
    yolo_enabled: bool = True
    process_fps: int = 3
    analysis_width: int = 640
    blur_threshold: float = 30.0
    min_brightness: float = 40.0
    max_brightness: float = 250.0
    ocr_every_n: int = 3
    # Text detection runs on a smaller copy: ~0.40 s vs ~0.70 s per frame at 640 on CPU.
    ocr_width: int = 480
    yolo_conf: float = 0.35
    # COCO stopgap until the Phase 6 custom model: class name -> role ("product" | "package").
    yolo_class_map: dict[str, str] = {
        "handbag": "product",
        "backpack": "product",
        "tie": "product",
        "umbrella": "product",
        "teddy bear": "product",
        "suitcase": "package",
    }
    # COCO has no apparel classes, so the contour heuristic still counts as "product".
    heuristic_product_fallback: bool = True
    max_upload_mb: int = 500
    cors_origins: list[str] = ["http://localhost:5173"]
    worker_poll_s: float = 1.5
    # A running job whose heartbeat is older than this is assumed lost and re-queued.
    job_stale_s: int = 300
    job_max_attempts: int = 3
    # "dev" auto-generates a JWT secret when none is set; any other env requires VMS_JWT_SECRET.
    env: str = "dev"
    jwt_secret: str | None = None
    jwt_ttl_hours: int = 12
    login_max_failures: int = 10
    login_window_s: int = 900
    # Lifetime of signed stream/evidence URLs handed out in API responses.
    media_url_ttl_s: int = 6 * 3600


@lru_cache
def get_settings() -> Settings:
    return Settings()
