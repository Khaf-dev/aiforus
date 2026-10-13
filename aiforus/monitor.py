"""What the assistant heard, saw and said - for an optional live view.

The assistant only *reports* here; it never draws. A display decides how to
show it: today the laptop preview window (:mod:`aiforus.preview`), later
for example a companion phone app. Nothing reported here is stored.

This module has no OpenCV dependency, so the assistant and its tests don't
need a GUI.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    import numpy as np

    from .i18n import Translator
    from .services.faces import FaceMatch
    from .services.spatial import Placement
    from .services.vision import Detection, TextRegion

Box = tuple[float, float, float, float]  # x1, y1, x2, y2 in pixels


class MarkKind(str, Enum):
    OBJECT = "object"
    NEAR = "near"  # cut off by the frame and large: very close
    KNOWN = "known"  # a recognised person
    UNKNOWN = "unknown"  # a face the assistant doesn't know
    TEXT = "text"


@dataclass(frozen=True)
class Mark:
    """One annotated region of a frame."""

    box: Box
    text: str
    kind: MarkKind


class Monitor(Protocol):
    def heard(self, text: str) -> None:
        """The user's command, as recognised."""

    def said(self, text: str) -> None:
        """A sentence the assistant starts speaking."""

    def answered(self, frame: np.ndarray, marks: list[Mark]) -> None:
        """The photo an answer was based on, with what was found in it."""


def short_distance(meters: float, tr: Translator) -> str:
    """Compact distance for labels: "<1 m", "~1,5 m", "~4 m"."""
    if meters < 1.0:
        return "<1 m"
    if meters < 3.0:
        return f"~{tr.number(round(meters * 2) / 2)} m"
    return f"~{round(meters)} m"


def object_marks(detections: list[Detection], placements: list[Placement], tr: Translator) -> list[Mark]:
    """ "kursi | jam 1 | ~2 m" for each detection (parallel lists)."""
    marks = []
    for detection, placement in zip(detections, placements, strict=True):
        parts = [tr.label(detection.label), tr.t("mark_clock", clock=placement.clock)]
        kind = MarkKind.OBJECT
        if placement.near:
            parts.append(tr.t("mark_near"))
            kind = MarkKind.NEAR
        elif placement.distance_m is not None:
            parts.append(short_distance(placement.distance_m, tr))
        marks.append(Mark(detection.box, " | ".join(parts), kind))
    return marks


def face_marks(placed: list[tuple[FaceMatch, int, float | None]], tr: Translator) -> list[Mark]:
    """ "Kaffa | jam 12 | ~1 m" for each (match, clock, distance)."""
    marks = []
    for match, clock, distance in placed:
        if match.box is None:
            continue
        x, y, w, h = match.box
        name = match.name or tr.t("mark_unknown")
        parts = [name, tr.t("mark_clock", clock=clock)]
        if distance is not None:
            parts.append(short_distance(distance, tr))
        kind = MarkKind.KNOWN if match.name else MarkKind.UNKNOWN
        marks.append(Mark((x, y, x + w, y + h), " | ".join(parts), kind))
    return marks


def text_marks(regions: list[TextRegion]) -> list[Mark]:
    return [Mark(r.box, r.text, MarkKind.TEXT) for r in regions if r.box is not None]
