"""Write the synthetic videos that ml/eval_labels.example.csv points at (dev/CI only)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from tests.fixtures.video_factory import make_video

CASES = {
    "qr_text_moving": {
        "qr_text": "AWB1234567",
        "text": "ORDER 42 SHIRT",
        "moving_box": True,
        "seconds": 12,
    },
    "qr_plain": {"qr_text": "AWB7654321", "seconds": 12},
    "text_only": {"text": "NO BARCODE HERE", "seconds": 12},
    "dark": {"qr_text": "AWB1111111", "dark": True, "seconds": 12},
    "blurred": {"qr_text": "AWB2222222", "blur": True, "seconds": 12},
    "too_short": {"qr_text": "AWB3333333", "seconds": 1},
}


def make_all(out_dir: Path) -> list[Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return [make_video(out_dir / f"{name}.mp4", **kw) for name, kw in CASES.items()]


if __name__ == "__main__":
    out = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/eval/synthetic")
    for path in make_all(out):
        print(path)
