"""Extract frames from inspection videos for YOLO annotation (CVAT / Roboflow).

    python ml/extract_frames.py --input data/samples --every-seconds 1 --max-per-video 60

Frames land in data/frames/<video name>/. Near-identical frames (perceptual hash) are skipped, so
a camera held still does not produce 30 copies of one image.
"""

import argparse
from pathlib import Path

import cv2
import numpy as np

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}
HASH_SIDE = 8  # 8x8 difference hash = 64 bits


def dhash(frame: np.ndarray) -> int:
    """64-bit difference hash: robust to small lighting and compression changes."""
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (HASH_SIDE + 1, HASH_SIDE), interpolation=cv2.INTER_AREA)
    bits = (small[:, 1:] > small[:, :-1]).flatten()
    return int("".join("1" if b else "0" for b in bits), 2)


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def extract_video(
    video: Path,
    out_dir: Path,
    *,
    every_seconds: float = 1.0,
    max_per_video: int | None = None,
    dedupe_distance: int = 5,
) -> int:
    """Save one frame per `every_seconds`, skipping frames within `dedupe_distance` bits of any
    kept frame. Returns the number saved."""
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        print(f"Failed to open {video}")
        return 0
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    step = max(1, round(fps * every_seconds))
    kept: list[int] = []
    idx = 0
    while max_per_video is None or len(kept) < max_per_video:
        ok, frame = cap.read()
        if not ok:
            break
        if idx % step == 0:
            h = dhash(frame)
            if all(hamming(h, k) > dedupe_distance for k in kept):
                if not kept:
                    out_dir.mkdir(parents=True, exist_ok=True)
                kept.append(h)
                cv2.imwrite(str(out_dir / f"{video.stem}_{idx:06d}.jpg"), frame)
        idx += 1
    cap.release()
    return len(kept)


def extract_frames(
    video_dir: Path,
    output_dir: Path,
    every_seconds: float = 1.0,
    max_per_video: int | None = None,
    dedupe_distance: int = 5,
) -> int:
    videos = sorted(p for p in video_dir.iterdir() if p.suffix.lower() in VIDEO_SUFFIXES)
    if not videos:
        print(f"No videos found in {video_dir}")
        return 0
    total = 0
    for video in videos:
        n = extract_video(
            video,
            output_dir / video.stem,
            every_seconds=every_seconds,
            max_per_video=max_per_video,
            dedupe_distance=dedupe_distance,
        )
        total += n
        print(f"{video.name}: {n} frames")
    print(f"\nDone: {total} images in {output_dir}")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Extract frames from videos for annotation.")
    parser.add_argument("--input", type=Path, default=Path("data/samples"))
    parser.add_argument("--output", type=Path, default=Path("data/frames"))
    parser.add_argument("--every-seconds", type=float, default=1.0)
    parser.add_argument("--max-per-video", type=int, default=None)
    parser.add_argument(
        "--dedupe-distance",
        type=int,
        default=5,
        help="skip frames within this many bits (of 64) of a kept frame; 0 keeps only exact dupes",
    )
    args = parser.parse_args()
    extract_frames(
        args.input,
        args.output,
        args.every_seconds,
        args.max_per_video,
        args.dedupe_distance,
    )
