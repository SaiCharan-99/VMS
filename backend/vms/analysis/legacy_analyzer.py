"""
VMS SOP analyzer (result shape v1).

Combines OpenCV heuristics, pyzbar barcode decoding and optional EasyOCR text density.
Phase 1 replaces this with the rubric-driven pipeline; the public API stays the same.
"""

import logging
from pathlib import Path

import cv2
import numpy as np

from vms.analysis.detectors import get_ocr_reader
from vms.config import get_settings

try:
    from pyzbar.pyzbar import decode as pyzbar_decode

    HAS_PYZBAR = True
except ImportError:  # zbar shared library missing
    HAS_PYZBAR = False

log = logging.getLogger(__name__)

OCR_EVERY_N_SAMPLES = 3
HIGH_MOTION_MAGNITUDE = 5.0


class VMSSOPAnalyzer:
    def __init__(
        self,
        blur_threshold: float | None = None,
        min_hold_sec: float = 2.0,
        process_fps: int | None = None,
        process_type: str = "Return",
    ) -> None:
        settings = get_settings()
        self.blur_threshold = settings.blur_threshold if blur_threshold is None else blur_threshold
        self.min_hold_sec = min_hold_sec
        self.process_fps = settings.process_fps if process_fps is None else process_fps
        self.process_type = process_type  # "Return" or "Forward"

    def _decision(self, total_score: int, confidence: float) -> tuple[str, str, float]:
        conf = round(float(confidence), 2)
        if total_score >= 85 and confidence >= 0.7:
            return "pass", "Accepted", conf
        if total_score >= 50 and confidence >= 0.4:
            return "review", "Review Required", conf
        return "fail", "Rejected", conf

    def _confidence_score(
        self, quality_failures: int, n: int, metrics: dict, barcode: str | None
    ) -> float:
        if n <= 0:
            return 0.0
        quality_ratio = 1.0 - min(quality_failures / n, 1.0)
        package_ratio = min(metrics.get("pct_package", 0) / 100.0, 1.0)
        label_ratio = min(metrics.get("pct_label", 0) / 100.0, 1.0)
        object_ratio = min(metrics.get("pct_obj", 0) / 100.0, 1.0)
        barcode_factor = 1.0 if barcode else 0.4

        confidence = (
            0.35 * quality_ratio
            + 0.25 * package_ratio
            + 0.20 * label_ratio
            + 0.10 * object_ratio
            + 0.10 * barcode_factor
        )
        return max(0.1, min(1.0, confidence))

    def _sample_video(self, path: str | Path) -> tuple[list[tuple[int, np.ndarray]], float]:
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Video file not found: {path}")
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            raise OSError(f"Cannot open video: {path}")

        video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / video_fps
        stride = max(1, int(video_fps / self.process_fps))

        frames = []
        idx = 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % stride == 0:
                h, w = frame.shape[:2]
                small = cv2.resize(frame, (640, int(h * 640 / w)), interpolation=cv2.INTER_AREA)
                frames.append((idx, small))
            idx += 1
        cap.release()
        return frames, duration

    def _quality(self, gray: np.ndarray) -> tuple[bool, float, float]:
        blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        bright = float(np.mean(gray))
        valid = blur >= self.blur_threshold and 10 <= bright <= 255
        return valid, blur, bright

    def _ai_detect_text(self, frame: np.ndarray) -> int:
        """Number of text blocks EasyOCR finds; 0 when OCR is unavailable."""
        reader = get_ocr_reader()
        if reader is None:
            return 0
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return len(reader.readtext(rgb, detail=0))

    def _try_barcode(self, frame: np.ndarray, gray: np.ndarray) -> str | None:
        if not HAS_PYZBAR:
            return None
        candidates = [frame, cv2.cvtColor(cv2.equalizeHist(gray), cv2.COLOR_GRAY2BGR)]
        for img in candidates:
            try:
                results = pyzbar_decode(img)
            except Exception:
                log.debug("pyzbar decode failed", exc_info=True)
                continue
            if results:
                return results[0].data.decode("utf-8")
        return None

    def _detect_label_region(self, gray: np.ndarray) -> bool:
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 30, 100)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        cnts, _ = cv2.findContours(
            cv2.dilate(edges, kernel, iterations=1), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        h, w = gray.shape
        for c in cnts:
            if h * w * 0.003 < cv2.contourArea(c) < h * w * 0.55:
                approx = cv2.approxPolyDP(c, 0.03 * cv2.arcLength(c, True), True)
                if 4 <= len(approx) <= 12:
                    _, _, rw, rh = cv2.boundingRect(c)
                    if 0.2 < rw / max(rh, 1) < 7.0:
                        return True
        return False

    def _detect_package_in_frame(self, gray: np.ndarray) -> tuple[bool, float]:
        blurred = cv2.GaussianBlur(gray, (7, 7), 0)
        _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape
        for c in cnts:
            if cv2.contourArea(c) > h * w * 0.15:
                return True, cv2.contourArea(c) / (h * w)
        return False, 0.0

    def _detect_small_tag(self, gray: np.ndarray) -> bool:
        edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 40, 120)
        cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        h, w = gray.shape
        return any(h * w * 0.001 < cv2.contourArea(c) < h * w * 0.07 for c in cnts)

    def _detect_rotation_direction(
        self, prev_gray: np.ndarray | None, curr_gray: np.ndarray
    ) -> tuple[int, float]:
        """Optical-flow rotation direction (1 / -1 / 0) and mean flow magnitude."""
        if prev_gray is None or prev_gray.shape != curr_gray.shape:
            return 0, 0.0
        flow = cv2.calcOpticalFlowFarneback(prev_gray, curr_gray, None, 0.5, 3, 15, 3, 5, 1.2, 0)
        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
        w = flow.shape[1]
        left_flow = float(np.mean(flow[:, : w // 2, 0]))
        right_flow = float(np.mean(flow[:, w // 2 :, 0]))
        if right_flow > left_flow:
            direction = 1
        elif left_flow > right_flow:
            direction = -1
        else:
            direction = 0
        return direction, float(np.mean(mag))

    @staticmethod
    def _rotation_metrics(directions: list[int], magnitudes: list[float]) -> tuple[int, int]:
        """Direction changes and an estimate of package sides shown (0–6)."""
        n = len(directions)
        if n == 0:
            return 0, 0
        direction_changes = 0
        prev_dir = 0
        for d in directions:
            if d != 0 and d != prev_dir:
                direction_changes += 1
                prev_dir = d
        sides = min(6, max(1, direction_changes + 1))
        high_motion = sum(1 for m in magnitudes if m > HIGH_MOTION_MAGNITUDE)
        if high_motion > n * 0.3:
            sides = min(6, sides + 2)
        return direction_changes, sides

    def analyze(self, video_path: str | Path) -> dict:
        frames, duration = self._sample_video(video_path)
        n = len(frames)

        label_flags, tag_flags, obj_flags, text_counts, package_flags = [], [], [], [], []
        directions: list[int] = []
        magnitudes: list[float] = []
        barcode = None
        quality_failures = 0
        prev_gray = None

        for sample_idx, (_, frame) in enumerate(frames):
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            direction, mag = self._detect_rotation_direction(prev_gray, gray)
            directions.append(direction)
            magnitudes.append(mag)
            prev_gray = gray

            valid, _, _ = self._quality(gray)
            if not valid:
                quality_failures += 1
                continue

            if sample_idx % OCR_EVERY_N_SAMPLES == 0:
                text_counts.append(self._ai_detect_text(frame))
            else:
                text_counts.append(text_counts[-1] if text_counts else 0)

            label_flags.append(self._detect_label_region(gray))
            pkg_detected, _ = self._detect_package_in_frame(gray)
            package_flags.append(pkg_detected)
            tag_flags.append(self._detect_small_tag(gray))
            obj_flags.append(pkg_detected)  # product treated like package until YOLO (Phase 1)

            if barcode is None:
                barcode = self._try_barcode(frame, gray)

        # Percentages are over quality-valid frames only.
        valid_n = n - quality_failures
        pct_label = sum(label_flags) / valid_n if valid_n else 0.0
        pct_tag = sum(tag_flags) / valid_n if valid_n else 0.0
        pct_obj = sum(obj_flags) / valid_n if valid_n else 0.0
        pct_package = sum(package_flags) / valid_n if valid_n else 0.0
        avg_text = float(np.mean(text_counts)) if text_counts else 0.0
        direction_changes, estimated_sides = self._rotation_metrics(directions, magnitudes)

        s1, s2, s3, s4 = 0, 0, 0, 0
        s1_notes, s2_notes, s3_notes, s4_notes = [], [], [], []

        # Step 1: Label (30)
        if avg_text > 5:
            s1 += 15
        else:
            s1_notes.append("No clear text/label detected. Hold label closer.")
        if barcode:
            s1 += 15
        else:
            s1_notes.append("Barcode not read. Ensure it is in focus.")

        # Step 2: Unboxing / Packing (20)
        if pct_package > 0.4:
            s2 += 10
        else:
            s2_notes.append("Package not consistently visible.")
        if duration > 10:
            s2 += 10
        else:
            s2_notes.append("Video too short for full process.")

        # Step 3: Tags (25)
        if pct_tag > 0.1:
            s3 += 15
        else:
            s3_notes.append("Brand tag not detected clearly.")
        if avg_text > 3:
            s3 += 10
        else:
            s3_notes.append("Tag text not readable.")

        # Step 4: Product (25)
        if pct_obj > 0.4:
            s4 += 25
        else:
            s4_notes.append("Product not visible enough.")

        total_score = s1 + s2 + s3 + s4
        confidence = self._confidence_score(
            quality_failures,
            n,
            {
                "pct_package": pct_package * 100,
                "pct_label": pct_label * 100,
                "pct_obj": pct_obj * 100,
            },
            barcode,
        )
        status, decision, conf = self._decision(total_score, confidence)

        return {
            "total_score": total_score,
            "status": status,
            "decision": decision,
            "confidence": conf,
            "duration_s": round(duration, 1),
            "detected_barcode": barcode,
            "frames_sampled": n,
            "quality_failures": quality_failures,
            "scores": {
                "shipping_label": {"score": s1, "notes": s1_notes},
                "unboxing": {"score": s2, "notes": s2_notes},
                "tags": {"score": s3, "notes": s3_notes},
                "product": {"score": s4, "notes": s4_notes},
            },
            "metrics": {
                "pct_label": round(pct_label * 100, 1),
                "pct_tag": round(pct_tag * 100, 1),
                "pct_obj": round(pct_obj * 100, 1),
                "pct_package": round(pct_package * 100, 1),
                "avg_text": round(avg_text, 1),
                "direction_changes": direction_changes,
                "estimated_sides": estimated_sides,
            },
        }
