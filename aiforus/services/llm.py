"""Answers to general questions via an LLM (optional).

Only used for utterances the intent router doesn't recognise. Safety-critical
routing never depends on it.
"""

from __future__ import annotations

import base64
import ipaddress
import logging
from enum import Enum
from typing import Any, Protocol
from urllib.parse import urlparse

from ..hal import ComponentUnavailable

logger = logging.getLogger(__name__)

_LANGUAGE_NAMES = {"id": "Bahasa Indonesia", "en": "English"}

SYSTEM_PROMPT = (
    "You are the voice of AIForUs, an assistant used by blind and low-vision people. "
    "Reply in {language}. Your reply is read aloud: at most three short sentences, "
    "no lists, no markdown, no URLs. You cannot see the user's surroundings in this "
    "conversation; if a question needs sight, say so and suggest the camera commands. "
    "Never tell the user that crossing a road, walking somewhere, or any physical action "
    "is safe."
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
    "You get one photo from the user's camera (held or worn at chest/eye level). "
    "Reply in {language}. Your reply is read aloud: plain sentences, no lists, no markdown. "
    "Only describe what is actually visible; if something is unclear or cut off, say so "
    "instead of guessing. Never say that a path is clear, that there are no obstacles, or "
    "that anything is safe."
)

VISION_TASKS = {
    VisionTask.DESCRIBE: (
        "Describe this scene in 3 to 5 short sentences: what kind of place it is, the main "
        "objects and people, and where they are using clock directions (12 o'clock is straight "
        "ahead, 3 o'clock is right, 9 o'clock is left). Mention important visible text."
    ),
    VisionTask.READ_DOCUMENT: (
        "Read the text in this image aloud in natural reading order, exactly as written. "
        "For a menu or receipt, read each item with its price. Do not invent missing words; "
        "say which part is blurry or cut off. If there is no readable text, say so."
    ),
    VisionTask.QUESTION: (
        "Answer this question about the image in at most three short sentences: {question} "
        "If you cannot tell from the image, say so."
    ),
}


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
    ) -> None:
        try:
            import openai
        except ImportError as exc:
            raise ComponentUnavailable("openai is not installed (pip install -e .[llm])") from exc
        self._client: Any = openai.AsyncOpenAI(
            api_key=api_key, base_url=base_url, timeout=timeout_s, max_retries=1
        )
        self._model = model
        self._max_tokens = max_tokens
        self._vision_model = vision_model or model
        self._vision_max_tokens = vision_max_tokens

    async def answer(self, question: str, language: str) -> str:
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT.format(language=_LANGUAGE_NAMES.get(language, "English")),
                },
                {"role": "user", "content": question},
            ],
            temperature=0.4,
            max_tokens=self._max_tokens,
        )
        return (response.choices[0].message.content or "").strip()

    async def look(
        self, image_jpeg: bytes, task: VisionTask, language: str, question: str | None = None
    ) -> str:
        """Ask the vision model about one JPEG image (OpenAI image_url format,
        which Ollama's OpenAI-compatible endpoint also accepts)."""
        instruction = VISION_TASKS[task].format(question=(question or "").strip())
        data_url = "data:image/jpeg;base64," + base64.b64encode(image_jpeg).decode("ascii")
        response = await self._client.chat.completions.create(
            model=self._vision_model,
            messages=[
                {
                    "role": "system",
                    "content": VISION_SYSTEM_PROMPT.format(language=_LANGUAGE_NAMES.get(language, "English")),
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
        )
        return (response.choices[0].message.content or "").strip()
