"""Synthetic inspection videos for tests."""

from pathlib import Path

import cv2
import numpy as np


def _qr_image(text: str, side: int) -> np.ndarray:
    import qrcode

    qr = qrcode.QRCode(version=2, box_size=10, border=4)
    qr.add_data(text)
    qr.make(fit=True)
    rgb = np.array(qr.make_image(fill_color="black", back_color="white").convert("RGB"))
    return cv2.resize(rgb[:, :, ::-1].copy(), (side, side), interpolation=cv2.INTER_AREA)


def make_video(
    path: Path,
    *,
    seconds: float = 2.0,
    fps: int = 10,
    size: tuple[int, int] = (320, 240),
    qr_text: str | None = None,
    text: str | None = None,
    moving_box: bool = False,
    blur: bool = False,
    dark: bool = False,
) -> Path:
    """Write an mp4 to `path`. `size` is (width, height)."""
    width, height = size
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"Cannot open VideoWriter for {path}")

    qr = _qr_image(qr_text, min(width, height) // 2) if qr_text else None
    n_frames = max(1, int(seconds * fps))
    for i in range(n_frames):
        frame = np.full((height, width, 3), 10 if dark else 245, dtype=np.uint8)
        if qr is not None:
            y, x = (height - qr.shape[0]) // 2, (width - qr.shape[1]) // 2
            frame[y : y + qr.shape[0], x : x + qr.shape[1]] = qr
        if text:
            cv2.putText(frame, text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (20, 20, 20), 2)
        if moving_box:
            box = width // 4
            x = int((width - box) * i / max(1, n_frames - 1))
            top = height // 3
            cv2.rectangle(frame, (x, top), (x + box, top + box), (40, 90, 160), -1)
        if blur:
            frame = cv2.GaussianBlur(frame, (31, 31), 0)
        writer.write(frame)
    writer.release()
    return path
