import sys
import types

import numpy as np
import pytest

from aiforus.hal import ComponentUnavailable
from aiforus.services.faces import OpenCVFaceEncoder, opencv_face_model_files


class FakeDetector:
    def __init__(self, rows):
        self.rows = rows
        self.input_size = None

    def setInputSize(self, size):  # noqa: N802 - OpenCV API
        self.input_size = size

    def detect(self, frame):
        return (1, None if self.rows is None else np.array(self.rows, dtype=np.float32))


class FakeRecognizer:
    def alignCrop(self, frame, row):  # noqa: N802 - OpenCV API
        return float(row[0])  # remember which face this is

    def feature(self, aligned):
        vec = np.zeros((1, 128), dtype=np.float32)
        vec[0, 0] = 3.0 + aligned
        vec[0, 1] = 4.0
        return vec


@pytest.fixture
def cv2(monkeypatch):
    state = {"rows": []}
    module = types.ModuleType("cv2")

    class FaceDetectorYN:
        @staticmethod
        def create(model, config, size, score, nms, top_k):
            state["detector_args"] = (model, size, score)
            state["detector"] = FakeDetector(state["rows"])
            return state["detector"]

    class FaceRecognizerSF:
        @staticmethod
        def create(model, config):
            state["recognizer_model"] = model
            return FakeRecognizer()

    module.FaceDetectorYN = FaceDetectorYN
    module.FaceRecognizerSF = FaceRecognizerSF
    monkeypatch.setitem(sys.modules, "cv2", module)
    return state


def make_models(directory, quantized=False):
    for _, name in opencv_face_model_files(quantized).values():
        (directory / name).write_bytes(b"onnx")


def row(x):
    return [x, 10, 50, 60] + [0] * 10 + [0.95]


def test_model_files_and_urls():
    files = opencv_face_model_files()
    assert files["detector"] == (
        "https://huggingface.co/opencv/face_detection_yunet/resolve/main/face_detection_yunet_2023mar.onnx",
        "face_detection_yunet_2023mar.onnx",
    )
    assert (
        opencv_face_model_files(quantized=True)["recognizer"][1] == "face_recognition_sface_2021dec_int8.onnx"
    )


def test_encodes_faces_left_to_right_as_unit_vectors(cv2, tmp_path):
    make_models(tmp_path)
    encoder = OpenCVFaceEncoder(tmp_path, score_threshold=0.7)
    cv2["detector"].rows = [row(300), row(20)]
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    encodings = encoder.encode(frame)
    assert cv2["detector"].input_size == (640, 480)
    assert len(encodings) == 2
    assert [round(e[0], 4) for e in encodings] == [
        round(23 / np.hypot(23, 4), 4),
        round(303 / np.hypot(303, 4), 4),
    ]
    assert all(np.linalg.norm(e) == pytest.approx(1.0) for e in encodings)
    assert cv2["detector_args"][2] == 0.7
    assert encoder.model_name == "sface-128"
    assert encoder.default_threshold == pytest.approx(1.128)


def test_no_faces(cv2, tmp_path):
    make_models(tmp_path)
    encoder = OpenCVFaceEncoder(tmp_path)
    cv2["detector"].rows = None
    assert encoder.encode(np.zeros((10, 10, 3), dtype=np.uint8)) == []


def test_quantized_models_use_separate_store_key(cv2, tmp_path):
    make_models(tmp_path, quantized=True)
    encoder = OpenCVFaceEncoder(tmp_path, quantized=True)
    assert encoder.model_name == "sface-128-int8"
    assert cv2["recognizer_model"].endswith("_int8.onnx")


def test_missing_models_point_to_download_command(cv2, tmp_path):
    with pytest.raises(ComponentUnavailable, match="download-models"):
        OpenCVFaceEncoder(tmp_path)


def test_model_load_error_is_reported(cv2, tmp_path, monkeypatch):
    import sys as _sys

    make_models(tmp_path)

    def broken(*args):
        raise RuntimeError("cv2.error: unsupported layer")

    monkeypatch.setattr(_sys.modules["cv2"].FaceDetectorYN, "create", staticmethod(broken))
    with pytest.raises(ComponentUnavailable, match="Could not load face models"):
        OpenCVFaceEncoder(tmp_path)


def test_old_opencv_is_reported(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "cv2", types.ModuleType("cv2"))
    with pytest.raises(ComponentUnavailable, match="4.8"):
        OpenCVFaceEncoder(tmp_path)


def test_cosine_threshold_equivalence():
    # For unit vectors |a-b|^2 = 2 - 2cos, so L2 1.128 == cosine 0.363.
    assert np.sqrt(2 - 2 * 0.363) == pytest.approx(1.128, abs=1e-3)


def test_detect_returns_boxes_left_to_right(cv2, tmp_path):
    make_models(tmp_path)
    encoder = OpenCVFaceEncoder(tmp_path)
    cv2["detector"].rows = [row(300), row(20)]
    boxes = encoder.detect(np.zeros((480, 640, 3), dtype=np.uint8))
    assert boxes == [(20.0, 10.0, 50.0, 60.0), (300.0, 10.0, 50.0, 60.0)]
