"""Image helpers for sending camera frames to a vision-language model."""

from __future__ import annotations

import numpy as np

from ..hal import ComponentUnavailable


def fit_within(width: int, height: int, max_side: int) -> tuple[int, int]:
    """Scale (width, height) down so the longer side is at most ``max_side``."""
    longest = max(width, height)
    if longest <= max_side:
        return width, height
    scale = max_side / longest
    return max(1, round(width * scale)), max(1, round(height * scale))


def encode_jpeg(frame: np.ndarray, max_side: int = 1024, quality: int = 85) -> bytes:
    """Downscale (smaller = faster for the model) and JPEG-encode a BGR frame."""
    try:
        import cv2
    except ImportError as exc:
        raise ComponentUnavailable("OpenCV is not installed (pip install -e .[vision])") from exc
    height, width = frame.shape[:2]
    new_w, new_h = fit_within(width, height, max_side)
    if (new_w, new_h) != (width, height):
        frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
    ok, buffer = cv2.imencode(".jpg", frame, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        raise RuntimeError("JPEG encoding failed")
    return buffer.tobytes()
