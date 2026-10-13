import sys
import types

import numpy as np
import pytest

from aiforus.services.imaging import encode_jpeg, fit_within


@pytest.mark.parametrize(
    "size, max_side, expected",
    [((1280, 720), 1024, (1024, 576)), ((640, 480), 1024, (640, 480)), ((720, 1280), 640, (360, 640))],
)
def test_fit_within(size, max_side, expected):
    assert fit_within(*size, max_side) == expected


def test_encode_jpeg_downscales_then_encodes(monkeypatch):
    calls = {}
    cv2 = types.ModuleType("cv2")
    cv2.INTER_AREA = 3
    cv2.IMWRITE_JPEG_QUALITY = 1

    def resize(frame, size, interpolation):
        calls["resize"] = size
        return np.zeros((size[1], size[0], 3), dtype=np.uint8)

    def imencode(ext, frame, params):
        calls["encode"] = (ext, frame.shape, params)
        return True, np.frombuffer(b"jpegbytes", dtype=np.uint8)

    cv2.resize, cv2.imencode = resize, imencode
    monkeypatch.setitem(sys.modules, "cv2", cv2)
    data = encode_jpeg(np.zeros((720, 1280, 3), dtype=np.uint8), max_side=1024, quality=80)
    assert data == b"jpegbytes"
    assert calls["resize"] == (1024, 576)
    assert calls["encode"] == (".jpg", (576, 1024, 3), [1, 80])
