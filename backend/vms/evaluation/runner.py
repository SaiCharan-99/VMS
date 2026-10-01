"""Run the pipeline once per video and cache its metrics (`--from-cache` skips the CV re-run)."""

import hashlib
import json
import logging
from dataclasses import dataclass
from pathlib import Path

from vms.analysis import analyze_video
from vms.analysis.detectors import model_card
from vms.analysis.metrics import METRIC_KEYS
from vms.analysis.result import MetricValue
from vms.config import Settings, get_settings
from vms.evaluation.labels import LabelRow

log = logging.getLogger(__name__)

# Settings that change the metrics a video produces. The rubric is NOT among them.
_ENGINE_FIELDS = (
    "process_fps", "analysis_width", "blur_threshold", "min_brightness", "max_brightness",
    "ocr_enabled", "ocr_every_n", "ocr_width", "yolo_enabled", "yolo_conf", "yolo_every_n",
    "tag_close_up_frac", "heuristic_product_fallback",
)  # fmt: skip


@dataclass(frozen=True)
class Measured:
    video: Path
    metrics: dict[str, MetricValue]
    runtime_ms: int
    engine: dict[str, object]
    cached: bool


def _fingerprint(settings: Settings, video: Path) -> str:
    """Changes when the video, the metric set, the engine settings or the model weights change."""
    st = video.stat()
    weights = settings.yolo_weights
    card = model_card.card_path(settings)
    parts = {
        "video": [str(video.resolve()), st.st_size, st.st_mtime_ns],
        "metrics": sorted(METRIC_KEYS),
        "settings": {f: getattr(settings, f) for f in _ENGINE_FIELDS},
        "weights": [weights.name, weights.stat().st_mtime_ns if weights.is_file() else None],
        "class_map": model_card.class_map(settings),
        "card": card.read_text(encoding="utf-8") if card.is_file() else None,
    }
    return hashlib.sha256(json.dumps(parts, sort_keys=True, default=str).encode()).hexdigest()[:24]


def measure(
    row: LabelRow,
    cache_dir: Path,
    *,
    settings: Settings | None = None,
    use_cache: bool = True,
    cache_only: bool = False,
) -> Measured | None:
    """Metrics for one labelled video. With `cache_only`, a cache miss returns None."""
    settings = settings or get_settings()
    key = _fingerprint(settings, row.video)
    entry = cache_dir / f"{row.video.stem}-{key}.json"
    if use_cache and entry.is_file():
        data = json.loads(entry.read_text(encoding="utf-8"))
        return Measured(row.video, data["metrics"], data["runtime_ms"], data["engine"], True)
    if cache_only:
        return None
    result = analyze_video(row.video, row.process_type, settings=settings)
    engine = {"version": result.engine.version, "detectors": result.engine.detectors}
    cache_dir.mkdir(parents=True, exist_ok=True)
    entry.write_text(
        json.dumps(
            {"metrics": result.metrics, "runtime_ms": result.timings_ms["total"], "engine": engine}
        ),
        encoding="utf-8",
    )
    return Measured(row.video, result.metrics, result.timings_ms["total"], engine, False)
