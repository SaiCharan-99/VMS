"""Extract frames from inspection videos for YOLO annotation (Roboflow / CVAT)."""

import argparse
from pathlib import Path

import cv2

VIDEO_SUFFIXES = {".mp4", ".avi", ".mov", ".mkv"}


def extract_frames(video_dir: Path, output_dir: Path, frame_skip: int = 15) -> int:
    """Save every `frame_skip`-th frame of each video in `video_dir`; return the count saved."""
    output_dir.mkdir(parents=True, exist_ok=True)
    videos = sorted(
        p for p in video_dir.iterdir() if p.suffix.lower() in VIDEO_SUFFIXES
    )
    if not videos:
        print(f"No videos found in {video_dir}")
        return 0

    total = 0
    for video_path in videos:
        cap = cv2.VideoCapture(str(video_path))
        if not cap.isOpened():
            print(f"Failed to open {video_path}")
            continue
        frame_idx = saved = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if frame_idx % frame_skip == 0:
                out = output_dir / f"{video_path.stem}_frame_{frame_idx:05d}.jpg"
                cv2.imwrite(str(out), frame)
                saved += 1
            frame_idx += 1
        cap.release()
        total += saved
        print(f"Extracted {saved} frames from {video_path.name}")

    print(f"\nDone! Extracted {total} images to {output_dir}")
    return total


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract frames from videos for ML training."
    )
    parser.add_argument("--input", type=Path, default=Path("data/samples"))
    parser.add_argument("--output", type=Path, default=Path("training_images"))
    parser.add_argument(
        "--skip", type=int, default=15, help="Extract 1 frame every N frames"
    )
    args = parser.parse_args()
    extract_frames(args.input, args.output, args.skip)
