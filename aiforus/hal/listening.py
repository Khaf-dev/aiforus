"""When the assistant listens, and capturing one spoken command.

Modes (``listening.mode``):

* ``wake_word``    - nothing leaves the machine until the assistant hears its
  name ("Hai Nemo") or the push-to-talk key is pressed. Then one command is
  recorded and transcribed.
* ``push_to_talk`` - only the key starts a command.
* ``always``       - every utterance is a command (the original behaviour,
  :class:`~aiforus.hal.stt.GoogleSpeechInput`).

Pipeline for the first two::

    microphone (16 kHz, 80 ms frames) -> wake detector / key
        -> trigger: beep + stop speaking
        -> record until the user stops talking -> transcriber -> text

The key also interrupts the assistant while it is speaking (barge-in). The
wake word does that only with a headset, otherwise the microphone would hear
the assistant say its own name. Heavy libraries are imported lazily.
"""

from __future__ import annotations

import collections
import json
import logging
import math
import sys
import threading
import time
from collections.abc import Callable, Iterator
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from . import ComponentUnavailable
from .stt import SpeechServiceError

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
FRAME_SAMPLES = 1280  # 80 ms; the frame size openWakeWord expects
FRAME_S = FRAME_SAMPLES / SAMPLE_RATE

# What the router understands as an emergency, per language.
EMERGENCY_TEXT = {"id": "darurat", "en": "emergency"}


class Trigger(str, Enum):
    WAKE = "wake"  # the assistant's name
    KEY = "key"  # push-to-talk
    EMERGENCY = "emergency"  # "tolong" / "help", heard without the name


# -- interfaces ----------------------------------------------------------------


class AudioSource(Protocol):
    def read(self) -> bytes:
        """One frame: FRAME_SAMPLES 16-bit mono samples at SAMPLE_RATE. Blocks."""

    def close(self) -> None: ...


class WakeDetector(Protocol):
    name: str
    # True if EMERGENCY is only reported for a whole, stand-alone utterance
    # ("tolong", not "tolong ambilkan air"). Otherwise the listener checks
    # that silence follows before acting on it.
    emergency_is_standalone: bool

    def process(self, frame: bytes) -> Trigger | None: ...

    def reset(self) -> None: ...


class KeyTrigger(Protocol):
    label: str

    def pressed(self) -> bool:
        """True once per key press. Never blocks."""


class Transcriber(Protocol):
    def transcribe(self, pcm: bytes, sample_rate: int, language: str) -> str | None:
        """Text, or None if nothing intelligible. Raises SpeechServiceError."""


def rms(frame: bytes) -> float:
    samples = np.frombuffer(frame, dtype="<i2").astype(np.float32)
    return float(math.sqrt(float(np.mean(samples * samples)))) if samples.size else 0.0


# -- recording one command -----------------------------------------------------


class CommandRecorder:
    """Energy-based end-of-speech detection.

    Waits up to ``start_timeout_s`` for speech, then records until
    ``end_silence_s`` of quiet or ``max_s`` in total. The threshold follows
    the background noise level measured while idle.
    """

    def __init__(
        self,
        *,
        start_timeout_s: float = 5.0,
        max_s: float = 10.0,
        end_silence_s: float = 0.8,
        min_rms: float = 300.0,
        ratio: float = 3.0,
    ) -> None:
        self.start_timeout_s = start_timeout_s
        self.max_s = max_s
        self.end_silence_s = end_silence_s
        self.min_rms = min_rms
        self.ratio = ratio

    def record(
        self, frames: Iterator[bytes], noise_rms: float, preroll: list[bytes] | None = None
    ) -> bytes | None:
        threshold = max(self.min_rms, noise_rms * self.ratio)
        collected = list(preroll or [])
        started = any(rms(f) >= threshold for f in collected)
        waited = silence = 0.0
        for frame in frames:
            loud = rms(frame) >= threshold
            collected.append(frame)
            if not started:
                waited += FRAME_S
                if loud:
                    started = True
                elif waited >= self.start_timeout_s:
                    return None
                else:
                    collected = collected[-4:]  # keep a short lead-in only
                continue
            silence = 0.0 if loud else silence + FRAME_S
            if silence >= self.end_silence_s or len(collected) * FRAME_S >= self.max_s:
                break
        return b"".join(collected) if started else None


# -- the listener ----------------------------------------------------------------


class TriggeredSpeechInput:
    """``SpeechInput`` for the wake-word and push-to-talk modes.

    Not half-duplex: it keeps listening while the assistant speaks so the key
    can interrupt it; the wake word is ignored meanwhile unless ``headset``.
    """

    half_duplex = False
    # After the assistant stops speaking, ignore the wake word this long
    # (room echo of its last words).
    ECHO_GUARD_S = 0.4
    PREROLL_FRAMES = 4

    def __init__(
        self,
        source: AudioSource,
        transcriber: Transcriber,
        *,
        language: str,
        detector: WakeDetector | None = None,
        key: KeyTrigger | None = None,
        recorder: CommandRecorder | None = None,
        headset: bool = False,
        emergency: bool = True,
    ) -> None:
        if detector is None and key is None:
            raise ValueError("Need a wake detector, a push-to-talk key, or both")
        self._source = source
        self._transcriber = transcriber
        self._language = language
        self.detector = detector
        self.key = key
        self._recorder = recorder or CommandRecorder()
        self._headset = headset
        self._emergency = emergency
        self._ring: collections.deque[bytes] = collections.deque(maxlen=self.PREROLL_FRAMES)
        self._noise = 200.0
        self._quiet_until = 0.0
        self._on_trigger: Callable[[Trigger], object] = lambda trigger: None
        self._is_speaking: Callable[[], bool] = lambda: False
        self.closed = False

    def attach(
        self,
        *,
        on_trigger: Callable[[Trigger], object] | None = None,
        is_speaking: Callable[[], bool] | None = None,
    ) -> None:
        """Hooks into the running assistant (called from the listener thread)."""
        if on_trigger is not None:
            self._on_trigger = on_trigger
        if is_speaking is not None:
            self._is_speaking = is_speaking

    def set_language(self, language: str) -> None:
        self._language = language

    def _frames(self) -> Iterator[bytes]:
        while not self.closed:
            yield self._source.read()

    def listen(self) -> str | None:
        for frame in self._frames():
            if self.key is not None and self.key.pressed():
                return self._capture(Trigger.KEY)
            now = time.monotonic()
            speaking = self._is_speaking()
            if speaking:
                self._quiet_until = now + self.ECHO_GUARD_S
                if not self._headset:
                    self._ring.append(frame)
                    continue  # don't let the assistant's own voice wake it
            elif now < self._quiet_until and not self._headset:
                self._ring.append(frame)
                continue
            else:
                self._noise = 0.95 * self._noise + 0.05 * rms(frame)
            self._ring.append(frame)
            if self.detector is None:
                continue
            trigger = self.detector.process(frame)
            if trigger is Trigger.EMERGENCY and self._emergency:
                self.detector.reset()
                if self.detector.emergency_is_standalone or self._silence_follows():
                    self._notify(Trigger.EMERGENCY)
                    return EMERGENCY_TEXT.get(self._language, "emergency")
                logger.info("'Tolong' inside a longer sentence - not an emergency")
            if trigger is Trigger.WAKE:
                return self._capture(Trigger.WAKE)
        return None

    # A cry for help is short; "tolong ambilkan air" keeps going.
    STANDALONE_WINDOW_S = 1.0
    STANDALONE_MAX_SPEECH_S = 0.32

    def _silence_follows(self) -> bool:
        threshold = max(self._recorder.min_rms, self._noise * self._recorder.ratio)
        speech = 0.0
        for _, frame in zip(range(round(self.STANDALONE_WINDOW_S / FRAME_S)), self._frames(), strict=False):
            self._ring.append(frame)
            if rms(frame) >= threshold:
                speech += FRAME_S
                if speech > self.STANDALONE_MAX_SPEECH_S:
                    return False
        return True

    def _notify(self, trigger: Trigger) -> None:
        try:
            self._on_trigger(trigger)
        except Exception:
            logger.exception("Trigger hook failed")

    def _capture(self, trigger: Trigger) -> str | None:
        logger.debug("Listening (%s)", trigger.value)
        self._notify(trigger)
        preroll = list(self._ring)
        self._ring.clear()
        audio = self._recorder.record(self._frames(), self._noise, preroll)
        if self.detector is not None:
            self.detector.reset()
        if audio is None:
            return None
        text = self._transcriber.transcribe(audio, SAMPLE_RATE, self._language)
        if text:
            logger.info("HEARD (%s, %s): %s", self._language, trigger.value, text)
        return text

    def close(self) -> None:
        self.closed = True
        self._source.close()


# -- adapters: microphone, key, transcriber, beep ------------------------------------


class PyAudioSource:
    """The default microphone as 16 kHz mono frames."""

    def __init__(self, device_index: int | None = None) -> None:
        try:
            import pyaudio
        except ImportError as exc:
            raise ComponentUnavailable("PyAudio is not installed (pip install -e .[voice])") from exc
        self._audio: Any = pyaudio.PyAudio()
        try:
            self._stream: Any = self._audio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=FRAME_SAMPLES,
                input_device_index=device_index,
            )
        except OSError as exc:
            self._audio.terminate()
            raise ComponentUnavailable(f"No usable microphone: {exc}") from exc
        self._lock = threading.Lock()

    def read(self) -> bytes:
        with self._lock:
            return self._stream.read(FRAME_SAMPLES, exception_on_overflow=False)

    def close(self) -> None:
        with self._lock:
            try:
                self._stream.stop_stream()
                self._stream.close()
            finally:
                self._audio.terminate()


class ConsoleKey:
    """Push-to-talk with a key in the console window (Windows).

    Glasses will use a hardware button instead; anything with ``pressed()``
    and ``label`` fits.
    """

    KEYS = {"space": " ", "enter": "\r"}

    def __init__(self, key: str = "space") -> None:
        if sys.platform != "win32":
            raise ComponentUnavailable("push-to-talk key is only supported in the Windows console for now")
        import msvcrt

        self._msvcrt: Any = msvcrt
        self._char = self.KEYS[key]
        self.label = key

    def pressed(self) -> bool:
        hit = False
        while self._msvcrt.kbhit():
            if self._msvcrt.getwch() == self._char:
                hit = True
        return hit


class GoogleTranscriber:
    """Google Web Speech via ``SpeechRecognition`` for recorded audio.

    Only the recorded command is sent - not everything the microphone hears.
    """

    def __init__(self, locales: dict[str, str]) -> None:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise ComponentUnavailable(
                "SpeechRecognition is not installed (pip install -e .[voice])"
            ) from exc
        self._sr: Any = sr
        self._recognizer = sr.Recognizer()
        self._locales = locales

    def transcribe(self, pcm: bytes, sample_rate: int, language: str) -> str | None:
        sr = self._sr
        audio = sr.AudioData(pcm, sample_rate, 2)
        try:
            return self._recognizer.recognize_google(audio, language=self._locales.get(language, "id-ID"))
        except sr.UnknownValueError:
            return None
        except sr.RequestError as exc:
            raise SpeechServiceError(str(exc)) from exc


def beep_pcm(frequency: float = 880.0, duration_s: float = 0.12, volume: float = 0.3) -> bytes:
    """A short sine "ting" with soft edges (no clicks), 16-bit mono."""
    t = np.arange(int(SAMPLE_RATE * duration_s)) / SAMPLE_RATE
    envelope = np.minimum(1.0, np.minimum(t, t[::-1]) / 0.01)
    wave = np.sin(2 * np.pi * frequency * t) * envelope * volume
    return (wave * 32767).astype("<i2").tobytes()


class Beeper:
    """Plays the "I'm listening" sound without blocking the listener."""

    def __init__(self) -> None:
        try:
            import pyaudio
        except ImportError as exc:
            raise ComponentUnavailable("PyAudio is not installed") from exc
        self._pyaudio: Any = pyaudio
        self._audio: Any = pyaudio.PyAudio()
        self._sound = beep_pcm()
        self._lock = threading.Lock()

    def play(self) -> None:
        threading.Thread(target=self._play, name="beep", daemon=True).start()

    def _play(self) -> None:
        with self._lock:
            try:
                stream = self._audio.open(
                    format=self._pyaudio.paInt16, channels=1, rate=SAMPLE_RATE, output=True
                )
                stream.write(self._sound)
                stream.stop_stream()
                stream.close()
            except OSError:
                logger.debug("Beep failed", exc_info=True)

    def close(self) -> None:
        self._audio.terminate()


# -- wake word engines ---------------------------------------------------------------

VOSK_MODEL_URL = "https://alphacephei.com/vosk/models/{name}.zip"


class VoskWakeDetector:
    """Keyword spotting with a small offline Vosk model restricted to a few
    words. No training needed, so it works today; less precise than a trained
    openWakeWord model. There is no Indonesian Vosk model, so the English one
    listens for the name (and "hi"/"hello" for "hai"/"halo") and for "help".
    """

    name = "vosk"
    emergency_is_standalone = True  # only whole utterances count (classify_keywords)

    def __init__(
        self,
        model_dir: Path,
        *,
        names: list[str],
        greetings: list[str],
        emergency_phrases: list[str],
    ) -> None:
        try:
            import vosk
        except ImportError as exc:
            raise ComponentUnavailable("vosk is not installed (pip install -e .[wake])") from exc
        if not model_dir.exists():
            raise ComponentUnavailable(
                f"Vosk model not found in {model_dir}. Download it with: python -m aiforus --download-models"
            )
        vosk.SetLogLevel(-1)
        self._model: Any = vosk.Model(str(model_dir))
        self._names = {n.lower() for n in names}
        missing = [n for n in self._names if not self._knows(n)]
        if missing:
            raise ComponentUnavailable(f"The Vosk model doesn't know the word(s) {missing}")
        phrases = set(self._names)
        phrases |= {f"{g} {n}" for g in greetings for n in self._names}
        self._emergency = {p.lower() for p in emergency_phrases if all(self._knows(w) for w in p.split())}
        phrases |= self._emergency
        self._grammar = json.dumps(sorted(phrases) + ["[unk]"])
        self._vosk: Any = vosk
        self.reset()

    def _knows(self, word: str) -> bool:
        # vosk >= 0.3.32; older versions can't tell, so trust the config.
        find = getattr(self._model, "vosk_model_find_word", None)
        return True if find is None else all(find(w) >= 0 for w in word.split())

    def reset(self) -> None:
        self._recognizer = self._vosk.KaldiRecognizer(self._model, SAMPLE_RATE, self._grammar)

    def process(self, frame: bytes) -> Trigger | None:
        if self._recognizer.AcceptWaveform(frame):
            text = json.loads(self._recognizer.Result()).get("text", "")
            final = True
        else:
            text = json.loads(self._recognizer.PartialResult()).get("partial", "")
            final = False
        return classify_keywords(text, self._names, self._emergency, final=final)


def classify_keywords(text: str, names: set[str], emergency: set[str], *, final: bool) -> Trigger | None:
    """The assistant's name anywhere -> WAKE (as soon as it's heard). An
    emergency phrase only when it was the *whole* utterance, so "help me
    with this" doesn't start emergency mode."""
    words = [w for w in text.lower().split() if w != "[unk]"]
    if any(w in names for w in words):
        return Trigger.WAKE
    if final and words and " ".join(words) in emergency and "[unk]" not in text:
        return Trigger.EMERGENCY
    return None


class OpenWakeWordDetector:
    """Trained openWakeWord models (ONNX): small, run on a Raspberry Pi or a
    phone, and can learn Indonesian phrases ("hai nemo", "tolong").

    Train them with ``tools/wakeword`` (Google Colab); each model scores every
    80 ms frame, a score above ``threshold`` triggers.
    """

    name = "openwakeword"
    emergency_is_standalone = False  # scores 80 ms frames; the listener checks for silence

    def __init__(
        self, wake_model: Path, emergency_model: Path | None = None, *, threshold: float = 0.5
    ) -> None:
        try:
            from openwakeword.model import Model
        except ImportError as exc:
            raise ComponentUnavailable("openwakeword is not installed (pip install -e .[wake])") from exc
        if not wake_model.exists():
            raise ComponentUnavailable(
                f"Wake word model {wake_model} not found. Train it with tools/wakeword (see its README)"
            )
        paths = [str(wake_model)]
        self._emergency_key: str | None = None
        if emergency_model is not None and emergency_model.exists():
            paths.append(str(emergency_model))
            self._emergency_key = emergency_model.stem
        try:
            self._model: Any = Model(wakeword_models=paths, inference_framework="onnx")
        except Exception as exc:  # missing feature models, bad file
            raise ComponentUnavailable(
                f"openWakeWord could not load its models ({exc}). Run: python -m aiforus --download-models"
            ) from exc
        self._wake_key = wake_model.stem
        self._threshold = threshold

    @property
    def listens_for_emergency(self) -> bool:
        return self._emergency_key is not None

    def process(self, frame: bytes) -> Trigger | None:
        scores = self._model.predict(np.frombuffer(frame, dtype="<i2"))
        if self._emergency_key is not None and scores.get(self._emergency_key, 0.0) >= self._threshold:
            return Trigger.EMERGENCY
        if scores.get(self._wake_key, 0.0) >= self._threshold:
            return Trigger.WAKE
        return None

    def reset(self) -> None:
        self._model.reset()
