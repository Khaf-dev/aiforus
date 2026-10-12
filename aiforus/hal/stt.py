"""Speech input adapters."""

from __future__ import annotations

import logging
from typing import Any, Protocol

from . import ComponentUnavailable

logger = logging.getLogger(__name__)


class SpeechServiceError(RuntimeError):
    """The recognizer couldn't reach its backend (e.g. no internet)."""


class SpeechInput(Protocol):
    # Half-duplex inputs (a real microphone) must not listen while the
    # assistant is talking, or they transcribe the assistant's own voice.
    half_duplex: bool
    closed: bool

    def listen(self) -> str | None:
        """Block until one utterance is captured. None on silence/unclear."""

    def set_language(self, language: str) -> None: ...

    def close(self) -> None: ...


class GoogleSpeechInput:
    """Microphone + Google Web Speech API via ``SpeechRecognition``.

    Note: this sends audio to Google and needs internet. An offline
    recognizer (whisper.cpp / faster-whisper) is planned for Fase 1.
    """

    half_duplex = True

    def __init__(
        self,
        *,
        locales: dict[str, str],
        language: str,
        timeout_s: float,
        phrase_limit_s: float,
        device_index: int | None = None,
    ) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise ComponentUnavailable(
                "SpeechRecognition is not installed (pip install -e .[voice])"
            ) from exc
        try:
            self._mic: Any = sr.Microphone(device_index=device_index)
        except (OSError, AttributeError) as exc:  # AttributeError: PyAudio missing
            raise ComponentUnavailable(f"No usable microphone (is PyAudio installed?): {exc}") from exc

        self._sr = sr
        self._recognizer = sr.Recognizer()
        self._locales = locales
        self._language = language
        self._timeout_s = timeout_s
        self._phrase_limit_s = phrase_limit_s
        self._calibrated = False
        self.closed = False

    def set_language(self, language: str) -> None:
        self._language = language

    def listen(self) -> str | None:
        sr = self._sr
        with self._mic as source:
            if not self._calibrated:
                self._recognizer.adjust_for_ambient_noise(source, duration=1)
                self._calibrated = True
            try:
                audio = self._recognizer.listen(
                    source, timeout=self._timeout_s, phrase_time_limit=self._phrase_limit_s
                )
            except sr.WaitTimeoutError:
                return None
        locale = self._locales.get(self._language, "id-ID")
        try:
            text = self._recognizer.recognize_google(audio, language=locale)
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            raise SpeechServiceError(str(exc)) from exc
        logger.info("HEARD (%s): %s", locale, text)
        return text

    def close(self) -> None:
        self.closed = True


class KeyboardInput:
    """Type commands instead of speaking them (``--text`` mode).

    Half-duplex too, so the prompt appears after the assistant's reply.
    """

    half_duplex = True

    def __init__(self, prompt: str = "Kamu: ") -> None:
        self._prompt = prompt
        self.closed = False

    def listen(self) -> str | None:
        try:
            return input(self._prompt)
        except EOFError:
            self.closed = True
            return None

    def set_language(self, language: str) -> None:
        self._prompt = "Kamu: " if language == "id" else "You: "

    def close(self) -> None:
        self.closed = True
