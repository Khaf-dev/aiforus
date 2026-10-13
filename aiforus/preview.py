"""Live preview window (``--preview``): what the camera sees and what the
assistant makes of it.

For developers, demos and sighted helpers - the assistant works exactly the
same without it. Two views:

* **live** - the camera with boxes from a light, throttled detection loop
  (objects with clock direction and distance, faces with names);
* **answer** - for a few seconds after a reply, the exact photo the reply
  was based on, with the same marks the assistant used. That makes it easy
  to check "what was said" against "what was seen".

Drawing (:func:`annotate`) is separate from showing (:class:`PreviewWindow`),
so another display - a phone app later - can reuse the same overlay.
Nothing is saved to disk.
"""

from __future__ import annotations

import contextlib
import logging
import threading
import time
import unicodedata
from typing import TYPE_CHECKING, Any, Protocol

import numpy as np

from .monitor import Mark, MarkKind, face_marks, object_marks
from .services.spatial import face_position, place, with_face_distances
from .services.vision import FrameQuality, assess_frame

if TYPE_CHECKING:
    from .config import Settings
    from .i18n import Translator
    from .services.faces import FaceService
    from .services.vision import ObjectDetector

logger = logging.getLogger(__name__)

# BGR
_COLORS = {
    MarkKind.OBJECT: (80, 200, 80),
    MarkKind.NEAR: (40, 40, 230),
    MarkKind.KNOWN: (230, 160, 40),
    MarkKind.UNKNOWN: (40, 160, 240),
    MarkKind.TEXT: (200, 80, 200),
}
_WHITE = (255, 255, 255)
_BLACK = (0, 0, 0)
_PLACEHOLDER_SIZE = (720, 1280)  # height, width


def ascii_text(text: str) -> str:
    """OpenCV's fonts only draw ASCII: "“Kafé” …" -> '"Kafe" ...'."""
    text = text.replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = text.replace("…", "...").replace("–", "-").replace("—", "-")
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def _wrap(cv2: Any, text: str, max_width: int, scale: float, thickness: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        width = cv2.getTextSize(candidate, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)[0][0]
        if width <= max_width or not current:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def annotate(
    frame: np.ndarray | None,
    marks: list[Mark],
    *,
    header: str = "",
    captions: list[str] | None = None,
    cv2: Any = None,
) -> np.ndarray:
    """A copy of ``frame`` with boxes, labels, a header and captions.

    ``frame`` None draws a black placeholder (no camera).
    """
    if cv2 is None:
        import cv2
    image = np.zeros((*_PLACEHOLDER_SIZE, 3), dtype=np.uint8) if frame is None else frame.copy()
    height, width = image.shape[:2]
    scale = max(0.4, 0.6 * width / 1280)
    thickness = 1 if width < 1000 else 2
    font = cv2.FONT_HERSHEY_SIMPLEX
    line_h = int(28 * scale / 0.6)
    header_h = line_h + 8 if header else 0

    for mark in marks:
        color = _COLORS.get(mark.kind, _WHITE)
        x1, y1, x2, y2 = (int(round(v)) for v in mark.box)
        cv2.rectangle(image, (x1, y1), (x2, y2), color, 2)
        label = ascii_text(mark.text)
        (tw, th), base = cv2.getTextSize(label, font, scale, thickness)
        top = y1 - th - base - 6
        if top < header_h:  # no room above the box (cut off at the top): inside it
            top = max(y1, header_h) + 2
        cv2.rectangle(image, (x1, top), (min(width - 1, x1 + tw + 8), top + th + base + 6), color, -1)
        cv2.putText(image, label, (x1 + 4, top + th + 3), font, scale, _BLACK, thickness, cv2.LINE_AA)

    if header:
        cv2.rectangle(image, (0, 0), (width, header_h), _BLACK, -1)
        cv2.putText(image, ascii_text(header), (8, line_h), font, scale, _WHITE, thickness, cv2.LINE_AA)

    lines: list[str] = []
    for caption in captions or []:
        lines += _wrap(cv2, ascii_text(caption), width - 16, scale, thickness)[:2]
    if lines:
        panel_top = height - len(lines) * line_h - 12
        overlay = image.copy()
        cv2.rectangle(overlay, (0, panel_top), (width, height), _BLACK, -1)
        image = cv2.addWeighted(overlay, 0.6, image, 0.4, 0)
        for i, line in enumerate(lines):
            y = panel_top + (i + 1) * line_h
            cv2.putText(image, line, (8, y), font, scale, _WHITE, thickness, cv2.LINE_AA)
    return image


class LatestFrame(Protocol):
    def latest(self) -> np.ndarray | None: ...


class PreviewWindow:
    """An OpenCV window on its own thread; implements :class:`~aiforus.monitor.Monitor`.

    Close it with ``q``, ``Esc`` or the window's close button; the assistant
    keeps running.
    """

    TITLE = "AIForUs preview"
    DETECT_INTERVAL_S = 0.3  # live detection is throttled to spare the CPU
    ANSWER_HOLD_S = 4.0  # how long the photo of an answer stays on screen
    FRAME_DELAY_MS = 30

    def __init__(
        self,
        camera: LatestFrame,
        *,
        settings: Settings,
        translator: Translator,
        detector: ObjectDetector | None = None,
        faces: FaceService | None = None,
        gui: Any = None,
    ) -> None:
        self._camera = camera
        self._settings = settings
        self._tr = translator
        self._detector = detector
        self._faces = faces
        self._gui = gui  # the cv2 module; injectable for tests
        self._lock = threading.Lock()
        self._heard = ""
        self._said = ""
        self._answer: tuple[np.ndarray, list[Mark], float] | None = None
        self._live_marks: list[Mark] = []
        self._live_status = ""
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.frames_shown = 0

    # -- Monitor -------------------------------------------------------------

    def heard(self, text: str) -> None:
        with self._lock:
            self._heard = text

    def said(self, text: str) -> None:
        with self._lock:
            self._said = text

    def answered(self, frame: np.ndarray, marks: list[Mark]) -> None:
        with self._lock:
            self._answer = (frame, list(marks), time.monotonic() + self.ANSWER_HOLD_S)

    # -- lifecycle -----------------------------------------------------------

    def start(self) -> None:
        if self._thread is None:
            self._thread = threading.Thread(target=self._run, name="preview", daemon=True)
            self._thread.start()

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=3)

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    # -- drawing loop ----------------------------------------------------------

    def _run(self) -> None:
        try:
            gui = self._gui
            if gui is None:
                import cv2 as gui
            gui.namedWindow(self.TITLE, gui.WINDOW_NORMAL)
        except Exception as exc:  # opencv-python-headless, no display, ...
            logger.warning(
                "Preview window unavailable (%s). It needs opencv-python with GUI support "
                "and a desktop session.",
                exc,
            )
            return
        logger.info("Preview window open - press q in it to close")
        next_detect = 0.0
        try:
            while not self._stop.is_set():
                now = time.monotonic()
                analyse = now >= next_detect
                if analyse:
                    next_detect = now + self.DETECT_INTERVAL_S
                image = self._render(now, analyse=analyse, cv2=gui)
                gui.imshow(self.TITLE, image)
                self.frames_shown += 1
                key = gui.waitKey(self.FRAME_DELAY_MS) & 0xFF
                if key in (27, ord("q")):
                    break
                if gui.getWindowProperty(self.TITLE, gui.WND_PROP_VISIBLE) < 1:
                    break
        except Exception:
            logger.exception("Preview window stopped")
        finally:
            with contextlib.suppress(Exception):
                gui.destroyWindow(self.TITLE)

    def _render(self, now: float, *, analyse: bool, cv2: Any = None) -> np.ndarray:
        with self._lock:
            answer = self._answer if self._answer is not None and now < self._answer[2] else None
            heard, said = self._heard, self._said
        captions = []
        if heard:
            captions.append(f"{self._tr.t('preview_heard')}: {heard}")
        if said:
            captions.append(f"{self._tr.t('preview_said')}: {said}")

        if answer is not None:
            frame, marks, _ = answer
            return annotate(frame, marks, header=self._tr.t("preview_answer"), captions=captions, cv2=cv2)

        frame = self._camera.latest()
        if frame is not None and analyse:
            self._live_marks, self._live_status = self._analyse(frame)
        header = self._tr.t("preview_live")
        if frame is None:
            header += " - " + self._tr.t("preview_no_camera")
        elif self._live_status:
            header += " - " + self._live_status
        marks = self._live_marks if frame is not None else []
        return annotate(frame, marks, header=header, captions=captions, cv2=cv2)

    def _analyse(self, frame: np.ndarray) -> tuple[list[Mark], str]:
        """Objects and faces in a live frame (never raises)."""
        camera = self._settings.camera
        quality = assess_frame(frame, camera.dark_threshold, camera.blank_std_threshold)
        if quality is FrameQuality.DARK:
            return [], self._tr.t("preview_dark")
        if quality is FrameQuality.BLANK:
            return [], self._tr.t("preview_blank")
        height, width = frame.shape[:2]
        fov = camera.horizontal_fov_deg
        face_height = self._settings.vision.face_height_m
        marks: list[Mark] = []
        try:
            matches = self._faces.identify(frame) if self._faces is not None else []
            if self._detector is not None:
                detections = self._detector.detect(frame)
                placements = [place(d, width, height, fov) for d in detections]
                boxes = [m.box for m in matches if m.box is not None]
                placements = with_face_distances(
                    placements, detections, boxes, width, height, fov, face_height
                )
                marks += object_marks(detections, placements, self._tr)
            placed = [
                (m, *face_position(m.box, width, height, fov, face_height))
                for m in matches
                if m.box is not None
            ]
            marks += face_marks(placed, self._tr)
        except Exception:
            logger.exception("Live detection failed")
        return marks, ""
