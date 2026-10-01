"""model_card.json: what `ml/train.py` writes next to the weights; drives the class -> role map."""

import json
import logging
from pathlib import Path

from vms.config import Settings

log = logging.getLogger(__name__)

ROLES = frozenset({"product", "package", "label", "barcode", "tag", "seal", "hand", "tool"})
# Default role of each annotated class (ml/dataset/README.md). Used by ml/train.py.
DEFAULT_CLASS_ROLES = {
    "shipping_label": "label",
    "barcode": "barcode",
    "brand_tag": "tag",
    "hangtag": "tag",
    "product": "product",
    "package_box": "package",
    "package_polybag": "package",
    "seal_tape": "seal",
    "hand": "hand",
    "scissors_cutter": "tool",
}


def card_path(settings: Settings) -> Path:
    return settings.yolo_model_card or settings.yolo_weights.with_suffix(".model_card.json")


def class_map(settings: Settings) -> dict[str, str]:
    """The model card's class map when one exists, else `settings.yolo_class_map`."""
    path = card_path(settings)
    if not path.is_file():
        return settings.yolo_class_map
    try:
        mapping = json.loads(path.read_text(encoding="utf-8"))["class_map"]
        unknown = sorted(set(mapping.values()) - ROLES)
        if unknown:
            raise ValueError(f"unknown roles {unknown}")
        return {str(k): str(v) for k, v in mapping.items()}
    except (OSError, ValueError, KeyError, TypeError) as exc:
        log.warning("Ignoring unreadable model card %s: %s", path, exc)
        return settings.yolo_class_map
