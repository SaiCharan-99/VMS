"""Train the VMS YOLOv8 detector and package it for the analyzer.

    python ml/train.py --data data/yolo/data.yaml --model yolov8s.pt --epochs 80

Writes data/models/<run>/ (ultralytics output), then copies best.pt to
data/models/vms-det-<date>.pt next to vms-det-<date>.model_card.json (metrics, classes,
class -> role map, data hash). Activate it with VMS_YOLO_WEIGHTS=data/models/vms-det-<date>.pt.
The card is found beside the weights, so switching models needs no code change.
"""

import argparse
import hashlib
import json
import shutil
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from vms.analysis.detectors.model_card import DEFAULT_CLASS_ROLES, ROLES

DATA_SUFFIXES = {".jpg", ".jpeg", ".png", ".txt"}


def dataset_hash(data_yaml: Path) -> str:
    """Hash of the config plus every image and label file name and size (fast, content-light)."""
    cfg = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    root = (data_yaml.parent / cfg.get("path", ".")).resolve()
    h = hashlib.sha256(data_yaml.read_bytes())
    for p in sorted(root.rglob("*")):
        if p.suffix.lower() in DATA_SUFFIXES:
            h.update(f"{p.relative_to(root).as_posix()}:{p.stat().st_size}".encode())
    return h.hexdigest()[:16]


def build_card(
    *,
    names: dict[int, str],
    metrics: dict[str, float],
    data_hash: str,
    base_model: str,
    epochs: int,
    imgsz: int,
    class_roles: dict[str, str] | None = None,
) -> dict[str, Any]:
    roles = {**DEFAULT_CLASS_ROLES, **(class_roles or {})}
    unknown = sorted(set(roles.values()) - ROLES)
    if unknown:
        raise ValueError(f"unknown roles: {unknown}")
    return {
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "base_model": base_model,
        "epochs": epochs,
        "imgsz": imgsz,
        "classes": [names[i] for i in sorted(names)],
        # A trained class with no known role stays out of the map, so the analyzer ignores it.
        "class_map": {n: roles[n] for n in names.values() if n in roles},
        "metrics": metrics,
        "data_hash": data_hash,
    }


def train(args: argparse.Namespace) -> Path:
    from ultralytics import YOLO

    data_yaml = args.data.resolve()
    run = args.run or f"vms-det-{datetime.now(UTC):%Y%m%d-%H%M}"
    model = YOLO(args.model)
    results = model.train(
        data=str(data_yaml),
        epochs=args.epochs,
        imgsz=args.imgsz,
        device=None if args.device == "auto" else args.device,  # None = best available
        project=str(args.out_dir.resolve()),
        name=run,
    )
    box = results.results_dict
    metrics = {
        "map50": round(float(box.get("metrics/mAP50(B)", 0.0)), 4),
        "map50_95": round(float(box.get("metrics/mAP50-95(B)", 0.0)), 4),
        "precision": round(float(box.get("metrics/precision(B)", 0.0)), 4),
        "recall": round(float(box.get("metrics/recall(B)", 0.0)), 4),
    }
    names = {int(k): v for k, v in results.names.items()}
    weights = args.out_dir / f"vms-det-{datetime.now(UTC):%Y-%m-%d}.pt"
    shutil.copy2(Path(results.save_dir) / "weights" / "best.pt", weights)
    card = build_card(
        names=names,
        metrics=metrics,
        data_hash=dataset_hash(data_yaml),
        base_model=args.model,
        epochs=args.epochs,
        imgsz=args.imgsz,
    )
    card_path = weights.with_suffix(".model_card.json")
    card_path.write_text(json.dumps(card, indent=2), encoding="utf-8")
    print(f"Weights: {weights}\nModel card: {card_path}\nmAP50: {metrics['map50']}")
    return weights


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("--data", type=Path, default=Path("data/yolo/data.yaml"))
    parser.add_argument("--model", default="yolov8s.pt", help="base weights (n/s/m/l)")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="auto", help="'auto' uses a GPU when there is one")
    parser.add_argument("--run", help="run name (default vms-det-<timestamp>)")
    parser.add_argument("--out-dir", type=Path, default=Path("data/models"))
    train(parser.parse_args())
