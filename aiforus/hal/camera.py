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

    def _read(self, flush: int) -> np.ndarray | None:
        for _ in range(flush):
            self._cap.grab()
        ok, frame = self._cap.read()
        return frame if ok and frame is not None else None

    def _grab(self, flush: int) -> np.ndarray | None:
        with self._lock:
            for attempt in range(2):  # reopen once if the device dropped
                if self._cap is None:
                    self._cap = self._open()
                    if self._cap is None:
                        return None
                frame = self._read(flush)
                if frame is not None:
                    return frame
                logger.warning("Camera read failed (attempt %d); reopening", attempt + 1)
                self._cap.release()
                self._cap = None
            return None

    def capture(self) -> np.ndarray | None:
        return self._grab(self._settings.flush_frames)

    def read_frame(self) -> np.ndarray | None:
        """The next frame without flushing - for a reader that never stops."""
        return self._grab(0)

    def close(self) -> None:
        with self._lock:
            if self._cap is not None:
                self._cap.release()
                self._cap = None


class FrameSource(Protocol):
    def read_frame(self) -> np.ndarray | None: ...

    def close(self) -> None: ...


class ContinuousCamera:
    """Reads a camera continuously on a background thread.

    Used with the live preview, so the preview and the assistant share one
    device. :meth:`capture` still waits for a frame taken *after* the call,
    like :class:`OpenCVCamera`, so answers describe now - and it's faster,
    because nothing has to be flushed.
    """

    def __init__(
        self, source: FrameSource, *, fresh_timeout_s: float = 2.0, retry_delay_s: float = 2.0
    ) -> None:
        self._source = source
        self._fresh_timeout_s = fresh_timeout_s
        self._retry_delay_s = retry_delay_s
        self._changed = threading.Condition()
        self._frame: np.ndarray | None = None
        self._seq = 0
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        with self._changed:
            if self._thread is None and not self._stop.is_set():
                self._thread = threading.Thread(target=self._run, name="camera-reader", daemon=True)
                self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                frame = self._source.read_frame()
            except Exception:
                logger.exception("Camera read failed")
                frame = None
            if frame is None:
                self._stop.wait(self._retry_delay_s)  # unplugged: retry, don't spin
                continue
            with self._changed:
                self._frame = frame
                self._seq += 1
                self._changed.notify_all()

    def latest(self) -> np.ndarray | None:
        """The newest frame (possibly a few ms old), or None."""
        with self._changed:
            return self._frame

    def capture(self) -> np.ndarray | None:
        self.start()
        with self._changed:
            target = self._seq + 1
            self._changed.wait_for(
                lambda: self._seq >= target or self._stop.is_set(), timeout=self._fresh_timeout_s
            )
            return self._frame if self._seq >= target else None

    def close(self) -> None:
        self._stop.set()
        with self._changed:
            self._changed.notify_all()
            thread = self._thread
        if thread is not None:
            thread.join(timeout=3)
        self._source.close()
