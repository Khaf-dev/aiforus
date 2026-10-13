"""Answers to general questions via an LLM (optional).

Only used for utterances the intent router doesn't recognise. Safety-critical
routing never depends on it.
"""

from __future__ import annotations

import base64
import ipaddress
import logging
from collections.abc import Callable
from datetime import date
from enum import Enum
from typing import Any, Protocol
from urllib.parse import urlparse

from ..hal import ComponentUnavailable

logger = logging.getLogger(__name__)

_LANGUAGE_NAMES = {"id": "Bahasa Indonesia", "en": "English"}

SYSTEM_PROMPT = (
    "You are the voice of AIForUs, an assistant used by blind and low-vision people. "
    "Today is {today} (mention it only when asked about the date or time). Reply in "
    "{language}. Your reply is read aloud: at most three short sentences, no lists, no "
    "markdown, no URLs. Answer only what was asked: do not offer more help and do not ask "
    "follow-up questions. Your knowledge stops at your training date and you cannot browse "
    "the internet. Only when the answer is a fact that changes over time (who holds an "
    "office, prices, news, schedules, weather), say that your information may be out of "
    "date; do not add that warning to other answers. You cannot see the user's surroundings "
    "in this conversation; if a question needs sight (what is in front, how many people, is "
    "there a ...), say so in one sentence and suggest 'apa di depan' or 'lihat, ...' (in "
    "English: 'what's in front' or 'look, ...'). Never tell the user that crossing a road, "
    "walking somewhere, or any physical action is safe."
)


class Answerer(Protocol):
    async def answer(self, question: str, language: str) -> str: ...


class VisionTask(str, Enum):
    DESCRIBE = "describe"
    READ_DOCUMENT = "read_document"
    QUESTION = "question"


class VisionAnswerer(Protocol):
    async def look(
        self, image_jpeg: bytes, task: VisionTask, language: str, question: str | None = None
    ) -> str: ...


VISION_SYSTEM_PROMPT = (
    "You are the eyes of AIForUs, an assistant for blind and low-vision people. "
    "You get one photo from the user's camera (held or worn at chest/eye level). It shows "
    "what is in front of the user; the user is not in it, so anyone visible is someone else. "
    "Reply in {language}. Your reply is read aloud: plain sentences, no lists, no markdown. "
    "{clock_hint} "
    "Only describe what is actually visible; if something is unclear or cut off, say so "
    "instead of guessing. Never say that a path is clear, that there are no obstacles, or "
    "that anything is safe."
)

# Written in the reply language: small models copy the example's wording, and
# translating "at 3 o'clock" literally gave "di 3 jam" (= "in 3 hours").
CLOCK_HINTS = {
    "id": (
        "Untuk arah, pakai posisi jam dengan kalimat seperti 'di arah jam 3': jam 12 lurus di "
        "depan, jam 3 di kanan, jam 9 di kiri. Kamera hanya melihat ke depan, jadi pakai jam 9, "
        "10, 11, 12, 1, 2 atau 3 saja; jam 4 sampai 8 ada di belakang pengguna. Bagian bawah "
        "foto biasanya lebih dekat, bukan 'jam 6'. Jangan menulis 'di 3 jam' atau '3 jam'."
    ),
    "en": (
        "For directions use clock positions, phrased like 'at 3 o'clock': 12 o'clock is straight "
        "ahead, 3 o'clock is to the right, 9 o'clock is to the left. The camera only looks "
        "forward, so use 9, 10, 11, 12, 1, 2 or 3 o'clock only; 4 to 8 are behind the user. "
        "The bottom of the photo is usually closer, not '6 o'clock'."
    ),
}

VISION_TASKS = {
    VisionTask.DESCRIBE: (
        "Describe this scene in 3 to 5 short sentences: what kind of place it is, the main "
        "objects and people, and where they are, using clock positions. Mention important "
        "visible text."
    ),
    VisionTask.READ_DOCUMENT: (
        "Read the text in this image aloud in natural reading order, exactly as written. "
        "For a menu or receipt, read each item with its price. Do not invent missing words; "
        "say which part is blurry or cut off. If there is no readable text, say so."
    ),
    VisionTask.QUESTION: (
        "Answer this question about the image in at most three short sentences: {question} "
        "If you cannot tell from the image, say so. {answer_hint}"
    ),
}

# A yes/no question must start with a clear verdict. gemma3:4b answered the
# same question twice with opposite, hedged sentences ("no key visible" /
# "there is a key, but I can't tell if it's on the table"). "Not visible" is
# not "absent", so the negative answer is phrased that way.
ANSWER_HINTS = {
    "id": (
        "Kalau pertanyaannya ya/tidak, mulai jawaban dengan tepat salah satu dari: 'Ya.', "
        "'Tidak terlihat.', atau 'Tidak yakin.', lalu jelaskan singkat di mana. Pilih 'Tidak "
        "yakin.' kalau bagian yang ditanyakan buram, tertutup, terpotong, atau kamu ragu. "
        "Jangan membuat kalimat yang saling bertentangan."
    ),
    "en": (
        "If it is a yes/no question, start your answer with exactly one of: 'Yes.', 'Not "
        "visible.', or 'Not sure.', then say briefly where. Choose 'Not sure.' if the part in "
        "question is blurry, hidden, cut off, or you have any doubt. Never contradict yourself."
    ),
}


_WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_MONTHS = (
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
)  # fmt: skip


def english_date(day: date) -> str:
    """ "Tuesday, 13 October 2026" - independent of the OS locale."""
    return f"{_WEEKDAYS[day.weekday()]}, {day.day} {_MONTHS[day.month - 1]} {day.year}"


def is_local_endpoint(base_url: str | None) -> bool:
    """True for servers on this machine or the local network (e.g. Ollama).

    ``None`` means the provider's default cloud endpoint.
    """
    if not base_url:
        return False
    host = (urlparse(base_url).hostname or "").lower()
    if host == "localhost" or host.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False
    return address.is_loopback or address.is_private or address.is_link_local


class OpenAIAnswerer:
    """Chat completions from any OpenAI-compatible server.

    That covers OpenAI itself and, through ``base_url``, local servers such
    as Ollama or llama.cpp as well as other hosted providers that expose the
    same API — so the assistant isn't locked to one vendor.
    """

    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        timeout_s: float,
        max_tokens: int,
        base_url: str | None = None,
        vision_model: str | None = None,
        vision_max_tokens: int = 400,
        vision_timeout_s: float = 60.0,
        today: Callable[[], date] = date.today,
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ComponentUnavailable("openai is not installed (pip install -e .[llm])") from exc
        # No automatic retries: a retry starts the whole request again (the
        # model re-reads the image), so the user would wait twice as long.
        # Each request carries its own timeout instead (see below).
        self._client: Any = openai.AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=0
        )
        self._model = model
        self._max_tokens = max_tokens
        self._timeout_s = timeout_s
        self._vision_model = vision_model or model
        self._vision_max_tokens = vision_max_tokens
        # Image requests are slower, and the first one also loads the model.
        self._vision_timeout_s = vision_timeout_s
        self._today = today

    async def answer(self, question: str, language: str) -> str:
        system = SYSTEM_PROMPT.format(
            language=_LANGUAGE_NAMES.get(language, "English"), today=english_date(self._today())
        )
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            temperature=0.4,
            max_tokens=self._max_tokens,
            timeout=self._timeout_s,
        )
        return (response.choices[0].message.content or "").strip()

    async def look(
        self, image_jpeg: bytes, task: VisionTask, language: str, question: str | None = None
    ) -> str:
        """Ask the vision model about one JPEG image (OpenAI image_url format,
        which Ollama's OpenAI-compatible endpoint also accepts)."""
        instruction = VISION_TASKS[task].format(
            question=(question or "").strip(),
            answer_hint=ANSWER_HINTS.get(language, ANSWER_HINTS["en"]),
        )
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_jpeg).decode("ascii")
        response = await self._client.chat.completions.create(
            model=self._vision_model,
            messages=[
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT.format(
                        language=_LANGUAGE_NAMES.get(language, "English"),
                        clock_hint=CLOCK_HINTS.get(language, CLOCK_HINTS["en"]),
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": instruction},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=self._vision_max_tokens,
            timeout=self._vision_timeout_s,
        )
        return (response.choices[0].message.content or "").strip()
