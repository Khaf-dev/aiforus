"""Camera adapters."""

from __future__ import annotations

import logging
import sys
import threading
from typing import Any, Protocol

import numpy as np

from ..config import CameraSettings
from . import ComponentUnavailable

logger = logging.getLogger(__name__)


class Camera(Protocol):
    def capture(self) -> np.ndarray | None:
        """Return a fresh BGR frame, or None if the camera is unavailable."""

    def close(self) -> None: ...


class OpenCVCamera:
    """Webcam via OpenCV, kept open between captures.

    Opening a webcam is slow and the first frames are dark while auto
    exposure settles, so the device stays open. Because OpenCV buffers
    frames, a few are grabbed and discarded before each read so the
    assistant describes *now*, not a few seconds ago.
    """

    _WARMUP_FRAMES = 10

    def __init__(self, settings: CameraSettings) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise ComponentUnavailable("OpenCV is not installed (pip install -e .[vision])") from exc
        self._cv2: Any = cv2
        self._settings = settings
        self._cap: Any = None
        self._lock = threading.Lock()

    def _open(self) -> Any:
        cv2 = self._cv2
        # DirectShow opens much faster than the default MSMF backend on Windows.
        backend = cv2.CAP_DSHOW if sys.platform == "win32" else cv2.CAP_ANY
        cap = cv2.VideoCapture(self._settings.index, backend)
        if not cap.isOpened():
            cap.release()
            logger.warning("Camera %d could not be opened", self._settings.index)
            return None
        if self._settings.width:
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self._settings.width)
        if self._settings.height:
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self._settings.height)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        for _ in range(self._WARMUP_FRAMES):
            cap.grab()
        return cap

    def _read(self) -> np.ndarray | None:
        for _ in range(self._settings.flush_frames):
            self._cap.grab()
        ok, frame = self._cap.read()
        return frame if ok and frame is not None else None

    def capture(self) -> np.ndarray | None:
        with self._lock:
            for attempt in range(2):  # reopen once if the device dropped
                if self._cap is None:
                    self._cap = self._open()
                    if self._cap is None:
                        return None
                frame = self._read()
                if frame is not None:
                    return frame
                logger.warning("Camera read failed (attempt %d); reopening", attempt + 1)
                self._cap.release()
                self._cap = None
            return None

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None
