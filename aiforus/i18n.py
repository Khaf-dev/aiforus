"""Small translation helper around :mod:`aiforus.locales`."""

from __future__ import annotations

import logging

from .config import SUPPORTED_LANGUAGES
from .locales import COCO_LABELS_ID, EN_IRREGULAR_PLURALS, MESSAGES

logger = logging.getLogger(__name__)


class Translator:
    """Formats spoken messages in the current language.

    Missing keys fall back to English and then to the key itself, so a
    catalog gap never crashes the assistant mid-sentence (tests catch gaps).
    """

    def __init__(self, language: str = "id") -> None:
        self._language = "id"
        self.language = language

    @property
    def language(self) -> str:
        return self._language

    @language.setter
    def language(self, value: str) -> None:
        if value not in SUPPORTED_LANGUAGES:
            raise ValueError(f"Unsupported language: {value!r}")
        self._language = value

    def t(self, key: str, **params: object) -> str:
        template = MESSAGES[self._language].get(key) or MESSAGES["en"].get(key)
        if template is None:
            logger.error("Missing message key: %s", key)
            return key
        return template.format(**params) if params else template

    # -- grammar helpers -------------------------------------------------

    def join(self, items: list[str]) -> str:
        """``a, b and c`` / ``a, b, dan c``."""
        items = [i for i in items if i]
        if not items:
            return ""
        if len(items) == 1:
            return items[0]
        conj = self.t("list_and")
        if len(items) == 2:
            return f"{items[0]} {conj} {items[1]}"
        head = ", ".join(items[:-1])
        # Indonesian uses a comma before "dan" in lists of three or more.
        if self._language == "id":
            return f"{head}, {conj} {items[-1]}"
        return f"{head} {conj} {items[-1]}"

    def label(self, coco_label: str) -> str:
        if self._language == "id":
            return COCO_LABELS_ID.get(coco_label, coco_label)
        return coco_label

    def count_label(self, coco_label: str, count: int) -> str:
        """``2 orang`` / ``2 people``."""
        if self._language == "id":
            return f"{count} {self.label(coco_label)}"
        if count == 1:
            return f"1 {coco_label}"
        plural = EN_IRREGULAR_PLURALS.get(coco_label)
        if plural is None:
            plural = coco_label + ("es" if coco_label.endswith(("s", "sh", "ch", "x")) else "s")
        return f"{count} {plural}"

    def number(self, value: float, decimals: int = 1) -> str:
        text = f"{value:.{decimals}f}"
        if text.endswith("." + "0" * decimals):
            text = text.split(".")[0]
        return text.replace(".", ",") if self._language == "id" else text

    def distance(self, meters: float) -> str:
        if meters < 1000:
            rounded = max(10, int(round(meters / 10.0)) * 10) if meters >= 5 else int(round(meters))
            return self.t("unit_meters", value=rounded)
        return self.t("unit_kilometers", value=self.number(meters / 1000.0))
