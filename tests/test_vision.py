import numpy as np

from aiforus.config import CameraSettings, VisionSettings
from aiforus.services.vision import (
    Detection,
    FrameQuality,
    TextRegion,
    VisionService,
    VisionStatus,
    assess_frame,
    sort_reading_order,
    summarize,
)
from tests.fakes import FakeCamera, flat_frame, textured_frame


def det(label, conf=0.9):
    return Detection(label, conf, (0, 0, 1, 1))


def test_assess_frame():
    assert assess_frame(flat_frame(5), 25, 6) is FrameQuality.DARK
    assert assess_frame(flat_frame(200), 25, 6) is FrameQuality.BLANK
    assert assess_frame(textured_frame(), 25, 6) is FrameQuality.OK


def test_summarize_counts_and_orders():
    dets = [det("chair", 0.6), det("person", 0.9), det("person", 0.8), det("cup", 0.95)]
    assert summarize(dets, 5) == [("person", 2), ("cup", 1), ("chair", 1)]
    assert summarize(dets, 1) == [("person", 2)]


def test_reading_order():
    regions = [
        TextRegion("b", 1, top=0, left=50),
        TextRegion("c", 1, top=100, left=0),
        TextRegion("a", 1, top=5, left=0),
    ]
    assert [r.text for r in sort_reading_order(regions)] == ["a", "b", "c"]


class StubDetector:
    def __init__(self, dets):
        self.dets = dets
        self.calls = 0

    def detect(self, frame):
        self.calls += 1
        return self.dets


class StubReader:
    def read(self, frame):
        return [TextRegion("JALAN SUDIRMAN", 0.9)]


def service(frames, detector=None, reader=None):
    return VisionService(FakeCamera(frames), detector, reader, CameraSettings(), VisionSettings())


async def test_look_reports_camera_problems_instead_of_nothing():
    detector = StubDetector([det("person")])
    assert (await service([], detector).look()).status is VisionStatus.NO_CAMERA
    assert (await service([flat_frame(3)], detector).look()).status is VisionStatus.DARK
    assert (await service([flat_frame(180)], detector).look()).status is VisionStatus.BLANK
    assert detector.calls == 0  # never runs detection on a useless frame


async def test_look_runs_requested_models():
    look = await service([textured_frame()], StubDetector([det("person")]), StubReader()).look(text=True)
    assert look.status is VisionStatus.OK
    assert [d.label for d in look.detections] == ["person"]
    assert [t.text for t in look.texts] == ["JALAN SUDIRMAN"]


async def test_look_unavailable_without_models():
    assert (await service([textured_frame()]).look()).status is VisionStatus.UNAVAILABLE
    vs = VisionService(None, StubDetector([]), None, CameraSettings(), VisionSettings())
    assert (await vs.look()).status is VisionStatus.UNAVAILABLE


def test_bgr_frame_dtype():
    assert textured_frame().dtype == np.uint8
