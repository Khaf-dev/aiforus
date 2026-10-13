from aiforus.i18n import Translator
from aiforus.monitor import MarkKind, face_marks, object_marks, short_distance, text_marks
from aiforus.services.faces import FaceMatch
from aiforus.services.spatial import Placement
from aiforus.services.vision import Detection, TextRegion


def test_short_distance():
    tr = Translator("id")
    assert [short_distance(d, tr) for d in (0.4, 1.0, 1.4, 2.8, 4.4)] == [
        "<1 m",
        "~1 m",
        "~1,5 m",
        "~3 m",
        "~4 m",
    ]
    assert short_distance(1.5, Translator("en")) == "~1.5 m"


def test_object_marks_label_direction_and_distance():
    detections = [Detection("chair", 0.9, (1, 2, 3, 4)), Detection("person", 0.8, (5, 6, 7, 8))]
    placements = [
        Placement("chair", 1, 30.0, 2.0, False, 0.9),
        Placement("person", 12, 0.0, None, True, 0.8),
    ]
    marks = object_marks(detections, placements, Translator("id"))
    assert [(m.text, m.kind, m.box) for m in marks] == [
        ("kursi | jam 1 | ~2 m", MarkKind.OBJECT, (1, 2, 3, 4)),
        ("orang | jam 12 | sangat dekat", MarkKind.NEAR, (5, 6, 7, 8)),
    ]
    english = object_marks(detections[:1], placements[:1], Translator("en"))
    assert english[0].text == "chair | 1 o'clock | ~2 m"


def test_face_and_text_marks_use_corner_boxes():
    placed = [
        (FaceMatch("Kaffa", 0.3, (10, 20, 30, 40)), 12, 1.2),
        (FaceMatch(None, 1.4, (100, 20, 30, 40)), 2, None),
        (FaceMatch("Siti", 0.2, None), 12, None),  # no box: nothing to draw
    ]
    marks = face_marks(placed, Translator("en"))
    assert [(m.text, m.kind, m.box) for m in marks] == [
        ("Kaffa | 12 o'clock | ~1 m", MarkKind.KNOWN, (10, 20, 40, 60)),
        ("unknown | 2 o'clock", MarkKind.UNKNOWN, (100, 20, 130, 60)),
    ]
    regions = [TextRegion("KELUAR", 0.9, box=(1, 1, 50, 20)), TextRegion("x", 0.9)]
    assert [(m.text, m.kind) for m in text_marks(regions)] == [("KELUAR", MarkKind.TEXT)]
