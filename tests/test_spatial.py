import math

import pytest

from aiforus.i18n import Translator
from aiforus.services.spatial import (
    bearing_deg,
    clock_from_bearing,
    group_placements,
    place,
    vertical_fov_deg,
)
from aiforus.services.vision import Detection

W, H = 1280, 720


def focal(hfov=70.0):
    vfov = math.radians(vertical_fov_deg(hfov, W, H))
    return (H / 2) / math.tan(vfov / 2)


def person_at(distance, center_x=640.0, label="person", height=1.65):
    h = height * focal() / distance
    return Detection(label, 0.9, (center_x - 30, 360 - h / 2, center_x + 30, 360 + h / 2))


@pytest.mark.parametrize(
    "angle, clock",
    [(0, 12), (14, 12), (16, 1), (30, 1), (-30, 11), (-46, 10), (60, 2), (90, 3), (-90, 9), (180, 6)],
)
def test_clock_from_bearing(angle, clock):
    assert clock_from_bearing(angle) == clock


def test_bearing_is_zero_in_the_middle_and_symmetric():
    assert bearing_deg(640, W, 70) == pytest.approx(0)
    assert bearing_deg(0, W, 70) == pytest.approx(-35)
    assert bearing_deg(W, W, 70) == pytest.approx(35)


@pytest.mark.parametrize("hfov, edge_clocks", [(70, (11, 1)), (120, (10, 2))])
def test_frame_edges_map_to_clock_by_field_of_view(hfov, edge_clocks):
    left = place(Detection("cup", 0.9, (0, 300, 2, 310)), W, H, hfov)
    right = place(Detection("cup", 0.9, (W - 2, 300, W, 310)), W, H, hfov)
    assert (left.clock, right.clock) == edge_clocks


@pytest.mark.parametrize("distance", [2.5, 3.0, 5.0, 10.0])
def test_distance_from_known_height(distance):
    placement = place(person_at(distance), W, H, 70)
    assert placement.distance_m == pytest.approx(distance, rel=1e-6)
    assert not placement.near


def test_cut_off_large_box_is_near_without_distance():
    placement = place(Detection("person", 0.9, (500, 0, 700, 720)), W, H, 70)
    assert placement.near
    assert placement.distance_m is None


def test_cut_off_small_box_has_no_distance_and_is_not_near():
    placement = place(Detection("person", 0.9, (500, 0, 520, 40)), W, H, 70)
    assert not placement.near
    assert placement.distance_m is None


def test_unknown_class_gets_direction_only():
    placement = place(Detection("laptop", 0.9, (900, 300, 1000, 380)), W, H, 70)
    assert placement.distance_m is None
    assert placement.clock == 1


def test_grouping_orders_nearest_first():
    placements = [
        place(person_at(5), W, H, 70),
        place(person_at(3), W, H, 70),
        place(person_at(2, center_x=1100, label="chair", height=0.9), W, H, 70),
        place(Detection("laptop", 0.9, (100, 300, 200, 380)), W, H, 70),
        place(Detection("person", 0.9, (500, 0, 700, 720)), W, H, 70),
    ]
    groups = group_placements(placements)
    summary = [(g.label, g.clock, g.count) for g in groups]
    # near first, then by distance, then unknown distance
    assert summary == [("person", 12, 3), ("chair", 1, 1), ("laptop", 11, 1)]
    assert groups[0].nearest.near


@pytest.mark.parametrize(
    "lang, meters, expected",
    [
        ("id", 0.4, "kurang dari 1 meter"),
        ("id", 1.74, "1,5 meter"),
        ("id", 2.3, "2,5 meter"),
        ("id", 7.4, "7 meter"),
        ("en", 1.0, "1 meter"),
        ("en", 2.6, "2.5 meters"),
        ("en", 0.5, "less than 1 meter"),
    ],
)
def test_approx_distance_for_speech(lang, meters, expected):
    assert Translator(lang).approx_distance(meters) == expected


def _faces_test_setup():
    from aiforus.services.spatial import with_face_distances

    f = focal()
    return with_face_distances, f


def test_cut_off_person_is_measured_by_face():
    with_face_distances, f = _faces_test_setup()
    det = Detection("person", 0.9, (500, 0, 800, 720))  # body cut off by the frame
    face_h = 0.21 * f / 1.6  # face of a person 1.6 m away
    faces = [(600, 100, face_h * 0.8, face_h)]
    [p] = with_face_distances([place(det, W, H, 70)], [det], faces, W, H, 70, 0.21)
    assert p.distance_m == pytest.approx(1.6)
    assert not p.near


def test_small_face_far_away_keeps_body_measurement():
    with_face_distances, f = _faces_test_setup()
    det = person_at(8)
    body = place(det, W, H, 70)
    tiny = [(630, 300, 20, 24)]  # < MIN_FACE_PX
    [p] = with_face_distances([body], [det], tiny, W, H, 70, 0.21)
    assert p.distance_m == pytest.approx(8)


def test_face_outside_the_person_box_and_other_classes_are_ignored():
    with_face_distances, f = _faces_test_setup()
    person = Detection("person", 0.9, (500, 0, 800, 720))
    chair = person_at(2, center_x=1100, label="chair", height=0.9)
    placements = [place(person, W, H, 70), place(chair, W, H, 70)]
    elsewhere = [(50, 100, 100, 120)]
    out = with_face_distances(placements, [person, chair], elsewhere, W, H, 70, 0.21)
    assert out == placements


def test_face_position_direction_and_distance():
    from aiforus.services.spatial import face_position, focal_length_px

    focal = focal_length_px(1280, 720, 70)
    h = 0.21 * focal / 2.0  # a face 2 m away
    clock, distance = face_position((640 - h / 2, 100, h, h), 1280, 720, 70, 0.21)
    assert clock == 12 and distance == pytest.approx(2.0)
    clock, distance = face_position((1200, 100, 8, 8), 1280, 720, 70, 0.21)
    assert clock == 1 and distance is None  # too small to measure
