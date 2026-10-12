"""Scene understanding: object detection (YOLOv8) and text reading (EasyOCR)."""

from __future__ import annotations

import asyncio
import logging
import threading
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Protocol

import numpy as np

from ..config import CameraSettings, VisionSettings
from ..hal import ComponentUnavailable
from ..hal.camera import Camera

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    box: tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


@dataclass(frozen=True)
class TextRegion:
    text: str
    confidence: float
    top: float = 0.0
    left: float = 0.0


class ObjectDetector(Protocol):
    def detect(self, frame: np.ndarray) -> list[Detection]: ...


class TextReader(Protocol):
    def read(self, frame: np.ndarray) -> list[TextRegion]: ...


class FrameQuality(Enum):
    OK = "ok"
    DARK = "dark"
    BLANK = "blank"


def assess_frame(frame: np.ndarray, dark_threshold: float, blank_std_threshold: float) -> FrameQuality:
    """Detect frames the assistant can't meaningfully describe, so it can say
    "I can't see" instead of "I see nothing" (which sounds like "all clear")."""
    gray = frame.mean(axis=2) if frame.ndim == 3 else frame
    if float(gray.mean()) < dark_threshold:
        return FrameQuality.DARK
    if float(gray.std()) < blank_std_threshold:
        return FrameQuality.BLANK
    return FrameQuality.OK


def summarize(detections: list[Detection], limit: int) -> list[tuple[str, int]]:
    """Group detections by label: most frequent first, then most confident."""
    counts = Counter(d.label for d in detections)
    best = {}
    for d in detections:
        best[d.label] = max(best.get(d.label, 0.0), d.confidence)
    ordered = sorted(counts, key=lambda label: (-counts[label], -best[label], label))
    return [(label, counts[label]) for label in ordered[:limit]]


class YoloDetector:
    """YOLOv8 via ultralytics, loaded on first use (or by ``warm_up``)."""

    def __init__(self, model_path: str, confidence: float) -> None:
        try:
            import ultralytics  # noqa: F401
        except ImportError as exc:
            raise ComponentUnavailable("ultralytics is not installed (pip install -e .[vision])") from exc
        self._model_path = model_path
        self._confidence = confidence
        self._model: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        if self._model is None:
            from ultralytics import YOLO

            logger.info("Loading detector %s", self._model_path)
            self._model = YOLO(self._model_path)
        return self._model

    def warm_up(self) -> None:
        with self._lock:
            self._load()

    def detect(self, frame: np.ndarray) -> list[Detection]:
        with self._lock:
            results = self._load()(frame, conf=self._confidence, verbose=False)
        detections: list[Detection] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
                detections.append(
                    Detection(result.names[int(box.cls[0])], float(box.conf[0]), (x1, y1, x2, y2))
                )
        return detections


class EasyOcrReader:
    """EasyOCR, loaded on first use (or by ``warm_up``)."""

    def __init__(self, languages: list[str], confidence: float) -> None:
        try:
            import easyocr  # noqa: F401
        except ImportError as exc:
            raise ComponentUnavailable("easyocr is not installed (pip install -e .[vision])") from exc
        self._languages = languages
        self._confidence = confidence
        self._reader: Any = None
        self._lock = threading.Lock()

    def _load(self) -> Any:
        if self._reader is None:
            import easyocr

            logger.info("Loading OCR for %s (first run downloads models)", self._languages)
            self._reader = easyocr.Reader(self._languages, gpu=False, verbose=False)
        return self._reader

    def warm_up(self) -> None:
        with self._lock:
            self._load()

    def read(self, frame: np.ndarray) -> list[TextRegion]:
        rgb = np.ascontiguousarray(frame[:, :, ::-1])  # BGR -> RGB without cv2
        with self._lock:
            raw = self._load().readtext(rgb)
        regions = []
        for points, text, prob in raw:
            if float(prob) < self._confidence or not str(text).strip():
                continue
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            regions.append(TextRegion(str(text).strip(), float(prob), float(min(ys)), float(min(xs))))
        return sort_reading_order(regions)


def sort_reading_order(regions: list[TextRegion], line_height: float = 25.0) -> list[TextRegion]:
    """Top-to-bottom, then left-to-right within a line."""
    return sorted(regions, key=lambda r: (round(r.top / line_height), r.left))


class VisionStatus(Enum):
    OK = "ok"
    NO_CAMERA = "no_camera"
    DARK = "dark"
    BLANK = "blank"
    UNAVAILABLE = "unavailable"


@dataclass
class Look:
    status: VisionStatus
    detections: list[Detection] = field(default_factory=list)
    texts: list[TextRegion] = field(default_factory=list)


class VisionService:
    def __init__(
        self,
        camera: Camera | None,
        detector: ObjectDetector | None,
        reader: TextReader | None,
        camera_settings: CameraSettings,
        vision_settings: VisionSettings,
    ) -> None:
        self.camera = camera
        self.detector = detector
        self.reader = reader
        self._camera_settings = camera_settings
        self.settings = vision_settings

    async def warm_up(self) -> None:
        """Load models in the background so the first request isn't slow."""
        for component in (self.detector, self.reader):
            warm = getattr(component, "warm_up", None)
            if warm is not None:
                try:
                    await asyncio.to_thread(warm)
                except Exception:
                    logger.exception("Warm-up failed for %s", type(component).__name__)

    async def look(self, *, objects: bool = True, text: bool = False) -> Look:
        if self.camera is None or (objects and self.detector is None) or (text and self.reader is None):
            return Look(VisionStatus.UNAVAILABLE)
        frame = await asyncio.to_thread(self.camera.capture)
        if frame is None:
            return Look(VisionStatus.NO_CAMERA)
        quality = assess_frame(
            frame, self._camera_settings.dark_threshold, self._camera_settings.blank_std_threshold
        )
        if quality is FrameQuality.DARK:
            return Look(VisionStatus.DARK)
        if quality is FrameQuality.BLANK:
            return Look(VisionStatus.BLANK)

        look = Look(VisionStatus.OK)
        if objects and self.detector is not None:
            look.detections = await asyncio.to_thread(self.detector.detect, frame)
        if text and self.reader is not None:
            look.texts = await asyncio.to_thread(self.reader.read, frame)
        return look
