"""Where things are: clock direction and rough distance from a detection.

Clock directions are the orientation convention taught to blind and
low-vision people: 12 o'clock is straight ahead, 3 o'clock is to the right,
9 o'clock to the left.

Distance uses the pinhole camera model with a typical real-world height per
object class::

    distance = real_height * focal_length_px / box_height_px

It is approximate (roughly +-30%): people sit, cars differ, objects can be
partially hidden. The assistant therefore always says "about", and the value
must never be used as a safety guarantee.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace

from .vision import Detection

# Typical full height in metres for classes whose height is fairly
# predictable. Classes not listed get a direction but no distance.
TYPICAL_HEIGHT_M: dict[str, float] = {
    "person": 1.65,
    "bicycle": 1.05,
    "motorcycle": 1.15,
    "car": 1.5,
    "bus": 3.2,
    "truck": 3.0,
    "fire hydrant": 0.8,
    "stop sign": 0.75,
    "bench": 0.85,
    "dog": 0.55,
    "cat": 0.3,
    "chair": 0.9,
    "couch": 0.85,
    "dining table": 0.75,
    "toilet": 0.75,
    "refrigerator": 1.7,
    "suitcase": 0.65,
    "backpack": 0.45,
    "bottle": 0.25,
    "cup": 0.1,
    "tv": 0.6,
}

# A box this close to the top/bottom edge is cut off by the frame, so its
# height in pixels underestimates the real object.
_EDGE_MARGIN_FRACTION = 0.02
# A cut-off box taller than this fraction of the frame is close to the camera.
_NEAR_HEIGHT_FRACTION = 0.6


@dataclass(frozen=True)
class Placement:
    label: str
    clock: int  # 1..12
    bearing_deg: float  # negative = left
    distance_m: float | None
    near: bool  # cut off by the frame and large: very close, distance unknown
    confidence: float

    @property
    def sort_key(self) -> tuple[int, float]:
        if self.near:
            return (0, 0.0)
        if self.distance_m is not None:
            return (1, self.distance_m)
        return (2, -self.confidence)


def vertical_fov_deg(horizontal_fov_deg: float, width: int, height: int) -> float:
    half = math.radians(horizontal_fov_deg) / 2
    return math.degrees(2 * math.atan(math.tan(half) * height / width))


def bearing_deg(center_x: float, width: int, horizontal_fov_deg: float) -> float:
    """Angle from straight ahead (pinhole model). Negative = left."""
    offset = (center_x / width) - 0.5  # -0.5 .. 0.5
    half = math.radians(horizontal_fov_deg) / 2
    return math.degrees(math.atan(2 * offset * math.tan(half)))


def clock_from_bearing(angle_deg: float) -> int:
    """0 deg -> 12, +30 -> 1, -30 -> 11, +90 -> 3."""
    hour = round(angle_deg / 30.0) % 12
    return 12 if hour == 0 else hour


def place(detection: Detection, width: int, height: int, horizontal_fov_deg: float) -> Placement:
    x1, y1, x2, y2 = detection.box
    angle = bearing_deg((x1 + x2) / 2, width, horizontal_fov_deg)
    box_height = max(1.0, y2 - y1)
    margin = _EDGE_MARGIN_FRACTION * height
    cut_off = y1 <= margin or y2 >= height - margin

    distance: float | None = None
    near = False
    real_height = TYPICAL_HEIGHT_M.get(detection.label)
    if cut_off:
        near = box_height >= _NEAR_HEIGHT_FRACTION * height
    elif real_height is not None:
        distance = real_height * focal_length_px(width, height, horizontal_fov_deg) / box_height

    return Placement(
        label=detection.label,
        clock=clock_from_bearing(angle),
        bearing_deg=angle,
        distance_m=distance,
        near=near,
        confidence=detection.confidence,
    )


def focal_length_px(width: int, height: int, horizontal_fov_deg: float) -> float:
    vfov = math.radians(vertical_fov_deg(horizontal_fov_deg, width, height))
    return (height / 2) / math.tan(vfov / 2)


# Below this face height (pixels) the face is too small to measure reliably,
# so the body height is used instead (~5 m away on a 720p, 70 deg webcam).
MIN_FACE_PX = 40.0


def with_face_distances(
    placements: list[Placement],
    detections: list[Detection],
    faces: list[tuple[float, float, float, float]],
    width: int,
    height: int,
    horizontal_fov_deg: float,
    face_height_m: float,
) -> list[Placement]:
    """Measure people by their face when it's visible.

    A webcam only sees a standing person from head to toe beyond ~2.5 m, so
    closer people are cut off by the frame and their body height can't be
    used. Their face usually is fully visible, and face height varies much
    less between adults than body height (and not at all when they sit).

    ``placements`` and ``detections`` must be parallel lists.
    """
    if not faces:
        return placements
    focal = focal_length_px(width, height, horizontal_fov_deg)
    result = []
    for placement, detection in zip(placements, detections, strict=True):
        if detection.label != "person":
            result.append(placement)
            continue
        x1, y1, x2, y2 = detection.box
        inside = [f for f in faces if x1 <= f[0] + f[2] / 2 <= x2 and y1 <= f[1] + f[3] / 2 <= y2]
        if not inside:
            result.append(placement)
            continue
        face_px = max(f[3] for f in inside)
        if placement.distance_m is None or face_px >= MIN_FACE_PX:
            distance = face_height_m * focal / max(face_px, 1.0)
            placement = replace(placement, distance_m=distance, near=False)
        result.append(placement)
    return result


@dataclass(frozen=True)
class PlacementGroup:
    """Objects of the same class in the same clock direction."""

    label: str
    clock: int
    count: int
    nearest: Placement


def group_placements(placements: list[Placement]) -> list[PlacementGroup]:
    """Group by (label, clock); nearest group first."""
    groups: dict[tuple[str, int], list[Placement]] = {}
    for p in placements:
        groups.setdefault((p.label, p.clock), []).append(p)
    result = []
    for (label, clock), members in groups.items():
        nearest = min(members, key=lambda p: p.sort_key)
        result.append(PlacementGroup(label, clock, len(members), nearest))
    return sorted(result, key=lambda g: g.nearest.sort_key)
