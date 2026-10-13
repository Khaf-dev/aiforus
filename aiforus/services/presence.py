"""Structured yes/no answers from a vision model: "is there a <thing>?".

Small vision models contradict themselves when they answer in free text
("Tidak terlihat. Ada kunci di atas meja ..."). So for presence questions the
model only fills in a small JSON object and *this* module decides what is
said: anything unclear or self-contradictory becomes "not sure", never a
confident yes or no.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from enum import Enum

PRESENCE_SYSTEM_PROMPT = (
    "You check one photo for an assistant used by blind and low-vision people. The photo "
    "shows what is in front of the user; the user is not in it. Reply with a JSON object "
    "only - no other text, no markdown."
)

PRESENCE_TASK = (
    'Is there {thing} in this photo? Reply with exactly this JSON: {{"visible": "yes" or '
    '"no" or "unsure", "clock": one of 9, 10, 11, 12, 1, 2, 3 or null, "detail": "at most 8 '
    'words in {language}, or an empty string"}}. '
    'Use "yes" only if you can clearly see it, and give its horizontal position as a clock '
    "position (12 = straight ahead, 3 = right, 9 = left). "
    'Use "unsure" if it might be there but is small, blurry, hidden or cut off, or if you '
    "have any doubt. "
    'Use "no" only if it is clearly not in the photo; then clock is null and detail is "".'
)

# A "yes" whose detail says the opposite ("tidak ada", "not visible") is a
# contradiction, which becomes "not sure".
_NEGATION = re.compile(
    r"\b(?:tidak|tak|bukan|belum|tanpa|no|not|none|nothing|without|cannot|can't|isn't|aren't)\b",
    re.IGNORECASE,
)
_FRONT_CLOCK = {9, 10, 11, 12, 1, 2, 3}
_MAX_DETAIL_WORDS = 12


class Verdict(str, Enum):
    YES = "yes"
    NOT_VISIBLE = "not_visible"
    UNSURE = "unsure"


@dataclass(frozen=True)
class Presence:
    verdict: Verdict
    clock: int | None = None
    detail: str = ""


UNSURE = Presence(Verdict.UNSURE)


def _json_object(text: str) -> dict | None:
    """The first JSON object in ``text``, tolerating code fences and chatter."""
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        value = json.loads(text[start : end + 1])
    except (ValueError, TypeError):
        return None
    return value if isinstance(value, dict) else None


def _clock(value: object) -> int | None:
    try:
        clock = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return clock if clock in _FRONT_CLOCK else None


def parse_presence(text: str) -> Presence:
    """Turn the model's reply into a consistent :class:`Presence`.

    Rules (anything else is UNSURE):

    * unreadable or unknown ``visible`` -> UNSURE
    * ``no`` with a position or a description -> contradiction -> UNSURE
    * ``yes`` whose detail contains a negation -> contradiction -> UNSURE
    * ``yes`` with a clock behind the user (4-8) keeps the yes, drops the clock
    """
    data = _json_object(text or "")
    if data is None:
        return UNSURE
    visible = str(data.get("visible", "")).strip().lower()
    detail = " ".join(str(data.get("detail") or "").split())
    clock = _clock(data.get("clock"))
    has_clock = data.get("clock") not in (None, "", "null")

    if visible == "no":
        return UNSURE if (has_clock or detail) else Presence(Verdict.NOT_VISIBLE)
    if visible != "yes":
        return UNSURE
    if _NEGATION.search(detail):
        return UNSURE
    if len(detail.split()) > _MAX_DETAIL_WORDS:
        detail = ""  # rambling; the verdict and position are what matter
    return Presence(Verdict.YES, clock, detail.rstrip(".!"))
