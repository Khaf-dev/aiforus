import sys
import threading
import time
import types

import numpy as np
import pytest

from aiforus.config import CameraSettings
from aiforus.hal.camera import ContinuousCamera, OpenCVCamera


class FakeCapture:
    def __init__(self):
        self.grabs = 0
        self.reads = 0

    def isOpened(self):  # noqa: N802 - OpenCV API
        return True

    def set(self, prop, value):
        pass

    def grab(self):
        self.grabs += 1
        return True

    def read(self):
        self.reads += 1
        return True, np.full((4, 4, 3), self.reads, dtype=np.uint8)

    def release(self):
        pass


@pytest.fixture
def fake_cv2(monkeypatch):
    captures = []
    module = types.SimpleNamespace(
        CAP_DSHOW=700,
        CAP_ANY=0,
        CAP_PROP_FRAME_WIDTH=3,
        CAP_PROP_FRAME_HEIGHT=4,
        CAP_PROP_BUFFERSIZE=38,
    )

    def video_capture(index, backend):
        captures.append(FakeCapture())
        return captures[-1]

    module.VideoCapture = video_capture
    monkeypatch.setitem(sys.modules, "cv2", module)
    return captures


def test_capture_flushes_but_read_frame_does_not(fake_cv2):
    camera = OpenCVCamera(CameraSettings(flush_frames=4))
    camera.capture()
    cap = fake_cv2[0]
    warmup = cap.grabs - 4
    camera.read_frame()
    assert cap.grabs == warmup + 4  # no extra grabs for read_frame
    assert cap.reads == 2


class ScriptedSource:
    """Hands out numbered frames; ``gate`` pauses it."""

    def __init__(self):
        self.count = 0
        self.closed = False
        self.gate = threading.Event()
        self.gate.set()
        self.fail = False

    def read_frame(self):
        self.gate.wait(1)
        time.sleep(0.002)
        if self.fail:
            return None
        self.count += 1
        return np.full((2, 2, 3), self.count % 255, dtype=np.uint8)

    def close(self):
        self.closed = True


def test_capture_returns_a_frame_taken_after_the_request():
    source = ScriptedSource()
    camera = ContinuousCamera(source)
    try:
        first = camera.capture()
        assert first is not None
        second = camera.capture()
        assert int(second[0, 0, 0]) > int(first[0, 0, 0])  # a new frame, not the cached one
        assert camera.latest() is not None
    finally:
        camera.close()
    assert source.closed


def test_capture_gives_up_when_the_camera_stops_delivering():
    source = ScriptedSource()
    source.fail = True
    camera = ContinuousCamera(source, fresh_timeout_s=0.1, retry_delay_s=0.01)
    try:
        started = time.monotonic()
        assert camera.capture() is None
        assert time.monotonic() - started < 1.0
    finally:
        camera.close()


def test_close_stops_the_reader_thread():
    source = ScriptedSource()
    camera = ContinuousCamera(source)
    camera.start()
    assert camera.capture() is not None
    camera.close()
    count = source.count
    time.sleep(0.05)
    assert source.count <= count + 1
