"""Text-to-speech adapters."""

from __future__ import annotations

import concurrent.futures
import logging
import queue
import sys
import threading
from typing import Any

from . import ComponentUnavailable

logger = logging.getLogger(__name__)


class Pyttsx3TTS:
    """Offline TTS via pyttsx3 (SAPI5 on Windows, espeak on Linux).

    pyttsx3 engines are not thread-safe, so a single dedicated thread owns
    the engine and executes commands sent to it. Interruption uses the
    engine's documented mechanism: calling ``engine.stop()`` from the
    ``started-word`` callback.
    """

    def __init__(
        self,
        *,
        rate: int,
        volume: float,
        voice_hints: dict[str, list[str]],
        language: str,
    ) -> None:
        try:
            import pyttsx3  # noqa: F401
        except ImportError as exc:
            raise ComponentUnavailable("pyttsx3 is not installed (pip install -e .[voice])") from exc

        self._voice_hints = voice_hints
        self._commands: queue.Queue[tuple[str, Any, concurrent.futures.Future[Any]]] = queue.Queue()
        self._lock = threading.Lock()
        self._issued = 0  # id of the most recently issued "say"
        self._cancel_upto = 0  # every "say" with id <= this is cancelled
        self._speaking_id = 0
        self._engine: Any = None
        self.voices: list[str] = []
        self.voice_found: dict[str, bool] = {}

        ready: concurrent.futures.Future[None] = concurrent.futures.Future()
        self._thread = threading.Thread(
            target=self._run, args=(rate, volume, language, ready), name="tts", daemon=True
        )
        self._thread.start()
        try:
            ready.result(timeout=15)
        except Exception as exc:
            raise ComponentUnavailable(f"TTS engine failed to start: {exc}") from exc

    # -- TextToSpeech protocol -------------------------------------------

    def speak(self, text: str) -> None:
        with self._lock:
            self._issued += 1
            say_id = self._issued
        self._submit("say", (say_id, text)).result()

    def interrupt(self) -> None:
        with self._lock:
            self._cancel_upto = self._issued
        engine = self._engine
        if engine is not None and self._speaking_id and self._speaking_id <= self._cancel_upto:
            try:  # best effort; the started-word callback is the reliable path
                engine.stop()
            except Exception:
                logger.debug("engine.stop() from caller thread failed", exc_info=True)

    def set_language(self, language: str) -> bool:
        return bool(self._submit("lang", language).result(timeout=10))

    def close(self) -> None:
        if self._thread.is_alive():
            self.interrupt()
            self._submit("quit", None)
            self._thread.join(timeout=3)

    # -- engine thread -----------------------------------------------------

    def _submit(self, command: str, arg: Any) -> concurrent.futures.Future[Any]:
        future: concurrent.futures.Future[Any] = concurrent.futures.Future()
        self._commands.put((command, arg, future))
        return future

    def _on_word(self, name: Any, location: int, length: int) -> None:
        if self._speaking_id and self._speaking_id <= self._cancel_upto:
            self._engine.stop()

    def _run(self, rate: int, volume: float, language: str, ready: concurrent.futures.Future[None]) -> None:
        if sys.platform == "win32":
            # SAPI5 is a COM API; COM must be initialised in every thread
            # that uses it, not just the main thread.
            try:
                import comtypes

                comtypes.CoInitialize()
            except Exception:
                logger.debug("COM initialisation failed", exc_info=True)
        try:
            import pyttsx3

            engine = pyttsx3.init()
            engine.setProperty("rate", rate)
            engine.setProperty("volume", volume)
            engine.connect("started-word", self._on_word)
            self._engine = engine
            self.voices = [f"{v.name} ({v.id})" for v in engine.getProperty("voices") or []]
            self._apply_language(language)
        except Exception as exc:
            ready.set_exception(exc)
            return
        ready.set_result(None)

        while True:
            command, arg, future = self._commands.get()
            try:
                if command == "quit":
                    future.set_result(None)
                    break
                if command == "say":
                    say_id, text = arg
                    if say_id > self._cancel_upto:
                        self._speaking_id = say_id
                        engine.say(text)
                        engine.runAndWait()
                    future.set_result(None)
                elif command == "lang":
                    future.set_result(self._apply_language(arg))
            except Exception as exc:
                logger.exception("TTS command %s failed", command)
                future.set_exception(exc)
            finally:
                self._speaking_id = 0

    def _apply_language(self, language: str) -> bool:
        hints = [h.lower() for h in self._voice_hints.get(language, [])]
        for voice in self._engine.getProperty("voices") or []:
            haystack = f"{voice.id} {voice.name} {getattr(voice, 'languages', '')}".lower()
            if any(hint in haystack for hint in hints):
                self._engine.setProperty("voice", voice.id)
                self.voice_found[language] = True
                logger.info("TTS voice for %s: %s", language, voice.name)
                return True
        self.voice_found[language] = False
        logger.warning(
            "No installed TTS voice matches language %r (hints: %s). Using the default voice; "
            "Indonesian text read by an English voice will sound wrong.",
            language,
            hints,
        )
        return False


class PrintTTS:
    """Prints what the assistant says; optionally also speaks via ``inner``.

    Used for ``--text`` mode and ``--mute``.
    """

    def __init__(self, inner: Any | None = None, prefix: str = "Asisten") -> None:
        self._inner = inner
        self._prefix = prefix

    def speak(self, text: str) -> None:
        print(f"{self._prefix}: {text}", flush=True)
        if self._inner is not None:
            self._inner.speak(text)

    def interrupt(self) -> None:
        if self._inner is not None:
            self._inner.interrupt()

    def set_language(self, language: str) -> bool:
        return self._inner.set_language(language) if self._inner is not None else True

    def close(self) -> None:
        if self._inner is not None:
            self._inner.close()
