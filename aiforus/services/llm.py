"""Answers to general questions via an LLM (optional).

Only used for utterances the intent router doesn't recognise. Safety-critical
routing never depends on it.
"""

from __future__ import annotations

import logging
from typing import Any, Protocol

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
