"""Face enrollment and recognition."""

from __future__ import annotations

import logging
import re
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..hal import ComponentUnavailable

logger = logging.getLogger(__name__)


class FaceEncoder(Protocol):
    def encode(self, frame: np.ndarray) -> list[np.ndarray]:
        """One encoding per face, ordered left to right."""


class FaceStore(Protocol):
    def add(self, name: str, vector: np.ndarray) -> int: ...
    def count(self, name: str) -> int: ...
    def all(self) -> dict[str, list[np.ndarray]]: ...
    def names(self) -> list[str]: ...
    def remove(self, name: str) -> bool: ...


OPENCV_MODEL_BASE_URL = "https://huggingface.co/opencv"
_OPENCV_MODELS = {
    # name: (repository, fp32 file, int8 file)
    "detector": (
        "face_detection_yunet",
        "face_detection_yunet_2023mar.onnx",
        "face_detection_yunet_2023mar_int8.onnx",
    ),
    "recognizer": (
        "face_recognition_sface",
        "face_recognition_sface_2021dec.onnx",
        "face_recognition_sface_2021dec_int8.onnx",
    ),
}


def opencv_face_model_files(quantized: bool = False) -> dict[str, tuple[str, str]]:
    """``{"detector"|"recognizer": (download URL, file name)}``.

    YuNet (MIT) and SFace (Apache-2.0) from the OpenCV model zoo, mirrored on
    Hugging Face: ~0.2 MB + ~39 MB, or ~0.1 MB + ~10 MB quantized.
    """
    files = {}
    for role, (repo, fp32, int8) in _OPENCV_MODELS.items():
        name = int8 if quantized else fp32
        files[role] = (f"{OPENCV_MODEL_BASE_URL}/{repo}/resolve/main/{name}", name)
    return files


class OpenCVFaceEncoder:
    """YuNet face detection + SFace embeddings via OpenCV's DNN module.

    Small ONNX models with no extra dependencies beyond OpenCV, so the same
    code runs on a laptop, a Raspberry Pi, a Jetson or (via OpenCV for
    Android) a phone. Embeddings are L2-normalised, so the Euclidean
    distance used by :class:`FaceService` maps directly onto SFace's cosine
    similarity: distance 1.128 == cosine 0.363 (OpenCV's recommended match).
    """

    default_threshold = 1.128

    def __init__(self, model_dir: Path, *, quantized: bool = False, score_threshold: float = 0.8) -> None:
        try:
            import cv2
        except ImportError as exc:
            raise ComponentUnavailable("OpenCV is not installed (pip install -e .[vision])") from exc
        if not hasattr(cv2, "FaceDetectorYN") or not hasattr(cv2, "FaceRecognizerSF"):
            raise ComponentUnavailable("OpenCV is too old for YuNet/SFace (need opencv-python >= 4.8)")

        files = opencv_face_model_files(quantized)
        paths = {role: model_dir / name for role, (_, name) in files.items()}
        missing = [p.name for p in paths.values() if not p.exists()]
        if missing:
            raise ComponentUnavailable(
                f"Face models not found in {model_dir} ({', '.join(missing)}). "
                "Download them with: python -m aiforus --download-models"
            )
        self.model_name = "sface-128-int8" if quantized else "sface-128"
        try:
            self._detector: Any = cv2.FaceDetectorYN.create(
                str(paths["detector"]), "", (320, 320), score_threshold, 0.3, 5000
            )
            self._recognizer: Any = cv2.FaceRecognizerSF.create(str(paths["recognizer"]), "")
        except Exception as exc:  # cv2.error: corrupt file, unsupported OpenCV build
            version = getattr(cv2, "__version__", "?")
            raise ComponentUnavailable(f"Could not load face models with OpenCV {version}: {exc}") from exc
        self._lock = threading.Lock()

    def encode(self, frame: np.ndarray) -> list[np.ndarray]:
        height, width = frame.shape[:2]
        with self._lock:
            self._detector.setInputSize((width, height))
            _, faces = self._detector.detect(frame)  # BGR, as captured by OpenCV
            if faces is None or len(faces) == 0:
                return []
            encodings = []
            # Each row: x, y, w, h, 5 landmark (x, y) pairs, score. Left to right.
            for row in sorted(faces, key=lambda r: float(r[0])):
                aligned = self._recognizer.alignCrop(frame, row)
                feature = np.asarray(self._recognizer.feature(aligned), dtype=np.float64).reshape(-1)
                norm = float(np.linalg.norm(feature))
                encodings.append(feature / norm if norm > 0 else feature)
        return encodings


class DlibFaceEncoder:
    """128-d face encodings from the ``face_recognition`` (dlib) library.

    Desktop only: dlib needs a C++ build and isn't practical on edge devices.
    """

    model_name = "dlib-128"
    default_threshold = 0.55

    def __init__(self, detection_model: str = "hog") -> None:
        try:
            import face_recognition  # noqa: F401
        except ImportError as exc:
            raise ComponentUnavailable("face_recognition is not installed (pip install -e .[faces])") from exc
        self._model = detection_model
        self._lock = threading.Lock()

    def encode(self, frame: np.ndarray) -> list[np.ndarray]:
        import face_recognition

        rgb = np.ascontiguousarray(frame[:, :, ::-1])  # BGR -> RGB
        with self._lock:
            locations: list[Any] = face_recognition.face_locations(rgb, model=self._model)
            encodings = face_recognition.face_encodings(rgb, locations)
        # (top, right, bottom, left): sort by left edge so names are spoken
        # in the order the user would scan the scene.
        paired = sorted(zip(locations, encodings, strict=True), key=lambda pair: pair[0][3])
        return [np.asarray(enc, dtype=np.float64) for _, enc in paired]


class EnrollStatus(Enum):
    OK = "ok"
    NO_FACE = "no_face"
    MULTIPLE_FACES = "multiple_faces"
    FULL = "full"
    INVALID_NAME = "invalid_name"


@dataclass(frozen=True)
class EnrollResult:
    status: EnrollStatus
    name: str
    samples: int = 0


@dataclass(frozen=True)
class FaceMatch:
    name: str | None  # None = unknown person
    distance: float


def normalize_name(raw: str) -> str:
    """ "budi  santoso!" -> "Budi Santoso"."""
    cleaned = re.sub(r"[^\w' -]", " ", raw, flags=re.UNICODE)
    return " ".join(part[:1].upper() + part[1:] for part in cleaned.split())[:100]


class FaceService:
    def __init__(
        self,
        encoder: FaceEncoder,
        store: FaceStore,
        *,
        match_threshold: float,
        max_samples_per_person: int,
    ) -> None:
        self._encoder = encoder
        self._store = store
        self._threshold = match_threshold
        self._max_samples = max_samples_per_person

    def enroll(self, raw_name: str, frame: np.ndarray) -> EnrollResult:
        name = normalize_name(raw_name)
        if not name:
            return EnrollResult(EnrollStatus.INVALID_NAME, name)
        existing = self._store.count(name)
        if existing >= self._max_samples:
            return EnrollResult(EnrollStatus.FULL, name, existing)
        encodings = self._encoder.encode(frame)
        if not encodings:
            return EnrollResult(EnrollStatus.NO_FACE, name, existing)
        if len(encodings) > 1:
            # Saving the wrong person's face would make every later
            # recognition of them wrong, so refuse instead of guessing.
            return EnrollResult(EnrollStatus.MULTIPLE_FACES, name, existing)
        samples = self._store.add(name, encodings[0])
        logger.info("Enrolled a face sample for %s (%d total)", name, samples)
        return EnrollResult(EnrollStatus.OK, name, samples)

    def identify(self, frame: np.ndarray) -> list[FaceMatch]:
        encodings = self._encoder.encode(frame)
        if not encodings:
            return []
        known = self._store.all()
        return [self._match(encoding, known) for encoding in encodings]

    def _match(self, encoding: np.ndarray, known: dict[str, list[np.ndarray]]) -> FaceMatch:
        best_name: str | None = None
        best_distance = float("inf")
        for name, samples in known.items():
            if not samples:
                continue
            distance = float(np.min(np.linalg.norm(np.stack(samples) - encoding, axis=1)))
            if distance < best_distance:
                best_name, best_distance = name, distance
        if best_name is not None and best_distance <= self._threshold:
            return FaceMatch(best_name, best_distance)
        return FaceMatch(None, best_distance)

    def known_people(self) -> list[str]:
        return self._store.names()

    def forget(self, raw_name: str) -> tuple[bool, str]:
        name = normalize_name(raw_name)
        return (self._store.remove(name) if name else False), name
