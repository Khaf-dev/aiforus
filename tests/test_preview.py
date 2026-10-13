import time

import numpy as np
import pytest

from aiforus.config import Settings
from aiforus.i18n import Translator
from aiforus.monitor import Mark, MarkKind
from aiforus.preview import PreviewWindow, annotate, ascii_text
from aiforus.services.faces import FaceMatch
from aiforus.services.vision import Detection
from tests.fakes import flat_frame, textured_frame

cv2 = pytest.importorskip("cv2")  # the CI installs no OpenCV


def test_ascii_text_keeps_labels_drawable():
    assert ascii_text("“Kafé” – jam 1…") == '"Kafe" - jam 1...'


def test_annotate_draws_on_a_copy():
    frame = np.full((360, 640, 3), 128, dtype=np.uint8)
    marks = [Mark((100, 100, 200, 220), "kursi | jam 1 | ~2 m", MarkKind.OBJECT)]
    image = annotate(frame, marks, header="LANGSUNG", captions=["Kamu: apa di depan"])
    assert image.shape == frame.shape
    assert (frame == 128).all()  # original untouched
    assert tuple(image[160, 100]) == (80, 200, 80)  # the box's left edge, object colour
    assert image[5, 5].sum() < 3 * 128  # dark header bar
    assert image[-5, 320].sum() < 3 * 128  # caption panel


def test_annotate_without_camera_draws_a_placeholder():
    image = annotate(None, [], header="LIVE - no camera")
    assert image.shape == (720, 1280, 3)


class LatestCamera:
    def __init__(self, frame):
        self.frame = frame

    def latest(self):
        return self.frame


class StubDetector:
    def detect(self, frame):
        return [Detection("chair", 0.9, (500, 300, 700, 500))]


class StubFaces:
    def identify(self, frame):
        return [FaceMatch("Kaffa", 0.2, (900, 200, 80, 100))]


def _window(frame, **kwargs):
    return PreviewWindow(
        LatestCamera(frame),
        settings=Settings(),
        translator=Translator("id"),
        detector=StubDetector(),
        faces=StubFaces(),
        **kwargs,
    )


def test_live_view_marks_objects_and_faces():
    window = _window(textured_frame(size=(720, 1280)))
    marks, status = window._analyse(window._camera.latest())
    assert status == ""
    assert [m.kind for m in marks] == [MarkKind.OBJECT, MarkKind.KNOWN]
    assert marks[0].text.startswith("kursi | jam 12")
    assert marks[1].text.startswith("Kaffa | jam 1")


def test_live_view_reports_dark_camera_instead_of_nothing():
    window = _window(flat_frame(3))
    assert window._analyse(flat_frame(3)) == ([], "terlalu gelap")


def test_answer_photo_is_held_then_live_view_returns():
    live = np.full((720, 1280, 3), 200, dtype=np.uint8)
    answer = np.full((720, 1280, 3), 30, dtype=np.uint8)
    window = _window(live)
    window.ANSWER_HOLD_S = 0.2
    window.heard("apa di depan")
    window.answered(answer, [])
    now = time.monotonic()
    shown = window._render(now, analyse=False)
    assert shown[360, 640].sum() == 3 * 30  # the answer's photo
    shown = window._render(now + 0.5, analyse=False)
    assert shown[360, 640].sum() == 3 * 200  # back to live


class FakeGui:
    """Stands in for cv2's window functions; closes after a few frames."""

    WINDOW_NORMAL = 0
    WND_PROP_VISIBLE = 4
    FONT_HERSHEY_SIMPLEX = cv2.FONT_HERSHEY_SIMPLEX
    LINE_AA = cv2.LINE_AA

    def __init__(self, frames_before_q=3):
        self.left = frames_before_q
        self.shown = []
        self.destroyed = False

    def __getattr__(self, name):  # drawing functions come from the real cv2
        return getattr(cv2, name)

    def namedWindow(self, title, flags):  # noqa: N802 - OpenCV API
        pass

    def imshow(self, title, image):
        self.shown.append(image.shape)

    def waitKey(self, delay):  # noqa: N802 - OpenCV API
        self.left -= 1
        return ord("q") if self.left <= 0 else -1

    def getWindowProperty(self, title, prop):  # noqa: N802 - OpenCV API
        return 1.0

    def destroyWindow(self, title):  # noqa: N802 - OpenCV API
        self.destroyed = True


def test_window_loop_shows_frames_and_closes_on_q():
    gui = FakeGui()
    window = _window(textured_frame(size=(720, 1280)), gui=gui)
    window.start()
    window._thread.join(2)
    assert not window.running
    assert gui.shown == [(720, 1280, 3)] * 3
    assert gui.destroyed


def test_window_without_gui_support_is_skipped_quietly(caplog):
    class NoGui:
        WINDOW_NORMAL = 0

        def namedWindow(self, *args):  # noqa: N802 - OpenCV API
            raise RuntimeError("The function is not implemented")

    window = _window(None, gui=NoGui())
    window.start()
    window._thread.join(2)
    assert not window.running
    assert "Preview window unavailable" in caplog.text
    window.close()


def test_label_of_a_box_cut_off_at_the_top_stays_visible():
    frame = np.full((720, 1280, 3), 128, dtype=np.uint8)
    marks = [Mark((60, 0, 330, 719), "orang | jam 11 | sangat dekat", MarkKind.NEAR)]
    image = annotate(frame, marks, header="LANGSUNG")
    # The red label sits just under the header bar, inside the box.
    row = image[48, 62:300]
    assert ((row == (40, 40, 230)).all(axis=1)).any()
