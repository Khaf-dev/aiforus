"""Piper neural text-to-speech (offline) with interruptible playback.

Piper runs the voice model locally with ONNX Runtime, so speech output works
without internet and sounds natural in Bahasa Indonesia, independent of the
voices installed in the operating system.

Licensing: the ``piper-tts`` package is GPL-3.0-or-later and is only used as
an optional extra; each voice model has its own license (see its model card).
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

import numpy as np

from . import ComponentUnavailable

logger = logging.getLogger(__name__)

VOICE_BASE_URL = "https://huggingface.co/rhasspy/piper-voices/resolve/main"


def voice_urls(voice_name: str) -> tuple[str, str]:
    """Model and config URLs for a voice such as ``id_ID-news_tts-medium``."""
    try:
        locale, name, quality = voice_name.split("-")
    except ValueError as exc:
        raise ValueError(f"Piper voice names look like 'id_ID-news_tts-medium', got {voice_name!r}") from exc
    family = locale.split("_")[0]
    base = f"{VOICE_BASE_URL}/{family}/{locale}/{name}/{quality}/{voice_name}"
    return f"{base}.onnx", f"{base}.onnx.json"


def voice_path(directory: Path, voice_name: str) -> Path:
    return directory / f"{voice_name}.onnx"


def download_voice(
    voice_name: str,
    directory: Path,
    *,
    session: Any = None,
    timeout_s: float = 60.0,
    progress: Callable[[str], None] | None = None,
) -> Path:
    """Download a voice's ``.onnx`` and ``.onnx.json`` unless already present."""
    from ..downloads import download_file

    model_url, config_url = voice_urls(voice_name)
    model_path = voice_path(directory, voice_name)
    config_path = model_path.with_name(model_path.name + ".json")
    download_file(config_url, config_path, session=session, timeout_s=timeout_s, progress=progress)
    download_file(model_url, model_path, session=session, timeout_s=timeout_s, progress=progress)
    return model_path


def _pcm16(chunk: Any) -> bytes:
    data = getattr(chunk, "audio_int16_bytes", None)
    if data is not None:
        return bytes(data)
    samples = np.clip(np.asarray(chunk.audio_float_array, dtype=np.float32), -1.0, 1.0)
    return (samples * 32767).astype("<i2").tobytes()


class PiperTTS:
    """``TextToSpeech`` implementation backed by Piper + PyAudio.

    Synthesis yields one audio chunk per sentence; playback writes small
    slices (~50 ms) and checks for interruption between them, so a more
    urgent message cuts in almost immediately.
    """

    engine_name = "piper"
    _WRITE_FRAMES = 1024

    def __init__(
        self,
        *,
        voices: dict[str, str],
        model_dir: Path,
        language: str,
        volume: float = 1.0,
        length_scale: float = 1.0,
    ) -> None:
        try:
            import piper
        except ImportError as exc:
            raise ComponentUnavailable("piper-tts is not installed (pip install -e .[piper])") from exc
        try:
            import pyaudio
        except ImportError as exc:
            raise ComponentUnavailable("PyAudio is not installed (pip install -e .[piper])") from exc

        self._piper: Any = piper
        self._pyaudio: Any = pyaudio
        self._voice_names = voices
        self._model_dir = model_dir
        self._loaded: dict[str, Any] = {}
        self._language = language
        self.voice_found: dict[str, bool] = {}

        try:
            self._syn_config: Any = piper.SynthesisConfig(volume=volume, length_scale=length_scale)
        except Exception:  # older/newer API without these fields
            logger.debug("SynthesisConfig unavailable; using voice defaults", exc_info=True)
            self._syn_config = None

        self._lock = threading.Lock()
        self._issued = 0  # id of the most recent speak() call
        self._cancel_upto = 0  # every speak() with id <= this stops

        if not self.set_language(language):
            raise ComponentUnavailable(
                f"Piper voice for {language!r} not found in {model_dir}. "
                "Download it with: python -m aiforus --download-models"
            )
        self._audio: Any = pyaudio.PyAudio()
        self._stream: Any = None
        self._stream_format: tuple[int, int] | None = None

    # -- voices --------------------------------------------------------------

    def _path(self, language: str) -> Path | None:
        name = self._voice_names.get(language)
        return voice_path(self._model_dir, name) if name else None

    def set_language(self, language: str) -> bool:
        path = self._path(language)
        if path is None or not path.exists():
            self.voice_found[language] = False
            logger.warning("No Piper voice model for %r (expected %s)", language, path)
            return False
        if language not in self._loaded:
            try:
                self._loaded[language] = self._piper.PiperVoice.load(str(path))
            except Exception:
                logger.exception("Failed to load Piper voice %s", path)
                self.voice_found[language] = False
                return False
        self._language = language
        self.voice_found[language] = True
        return True

    # -- TextToSpeech protocol -------------------------------------------------

    def speak(self, text: str) -> None:
        with self._lock:
            self._issued += 1
            speak_id = self._issued
        voice = self._loaded.get(self._language)
        if voice is None:
            return
        for chunk in voice.synthesize(text, syn_config=self._syn_config):
            if self._cancelled(speak_id):
                return
            pcm = _pcm16(chunk)
            channels = int(getattr(chunk, "sample_channels", 1) or 1)
            stream = self._ensure_stream(int(chunk.sample_rate), channels)
            step = self._WRITE_FRAMES * 2 * channels
            for start in range(0, len(pcm), step):
                if self._cancelled(speak_id):
                    return
                stream.write(pcm[start : start + step])

    def interrupt(self) -> None:
        with self._lock:
            self._cancel_upto = self._issued

    def close(self) -> None:
        self.interrupt()
        if self._stream is not None:
            try:
                self._stream.stop_stream()
                self._stream.close()
            except Exception:
                logger.debug("Closing audio stream failed", exc_info=True)
            self._stream = None
        self._audio.terminate()

    # -- internals ---------------------------------------------------------------

    def _cancelled(self, speak_id: int) -> bool:
        return speak_id <= self._cancel_upto

    def _ensure_stream(self, rate: int, channels: int) -> Any:
        if self._stream is None or self._stream_format != (rate, channels):
            if self._stream is not None:
                self._stream.close()
            self._stream = self._audio.open(
                format=self._audio.get_format_from_width(2), channels=channels, rate=rate, output=True
            )
            self._stream_format = (rate, channels)
        return self._stream
