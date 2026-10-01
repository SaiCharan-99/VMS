"""Contour heuristics carried over from the v1 analyzer; the fallback without a trained model."""

import cv2
import numpy as np


def detect_label_region(gray: np.ndarray) -> bool:
    """A medium-sized quadrilateral-ish contour, like a shipping label."""
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


def detect_package(gray: np.ndarray) -> bool:
    """An Otsu blob covering more than 15% of the frame."""
    blurred = cv2.GaussianBlur(gray, (7, 7), 0)
    _, thresh = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    cnts, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    return any(cv2.contourArea(c) > h * w * 0.15 for c in cnts)


def detect_small_tag(gray: np.ndarray) -> bool:
    """Any small closed edge contour, like a hangtag."""
    edges = cv2.Canny(cv2.GaussianBlur(gray, (3, 3), 0), 40, 120)
    cnts, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape
    return any(h * w * 0.001 < cv2.contourArea(c) < h * w * 0.07 for c in cnts)
