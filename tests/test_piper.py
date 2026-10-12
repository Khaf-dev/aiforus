import sys
import threading
import time
import types
from dataclasses import dataclass

import numpy as np
import pytest

from aiforus.config import Settings
from aiforus.hal import ComponentUnavailable
from aiforus.hal.piper_tts import PiperTTS, download_voice, voice_urls

RATE = 22050


@dataclass
class FakeChunk:
    sample_rate: int
    sample_width: int
    sample_channels: int
    audio_float_array: np.ndarray


class FakeVoice:
    def __init__(self, path):
        self.path = path
        self.config = types.SimpleNamespace(sample_rate=RATE)
        self.calls = []

    def synthesize(self, text, syn_config=None):
        self.calls.append((text, syn_config))
        for _sentence in [s for s in text.split(".") if s.strip()]:
            # 0.2 s of audio per sentence
            yield FakeChunk(RATE, 2, 1, np.full(int(RATE * 0.2), 0.5, dtype=np.float32))


class FakeStream:
    def __init__(self, rate):
        self.rate = rate
        self.written = 0
        self.closed = False

    def write(self, data):
        self.written += len(data)
        time.sleep(len(data) / 2 / self.rate)  # play in real time

    def stop_stream(self):
        pass

    def close(self):
        self.closed = True


class FakePyAudio:
    def __init__(self):
        self.streams = []
        self.terminated = False

    def get_format_from_width(self, width):
        return width

    def open(self, format, channels, rate, output):
        stream = FakeStream(rate)
        self.streams.append(stream)
        return stream

    def terminate(self):
        self.terminated = True


@pytest.fixture
def fakes(monkeypatch, tmp_path):
    piper = types.ModuleType("piper")

    class PiperVoice:
        load = staticmethod(lambda path: FakeVoice(path))

    @dataclass
    class SynthesisConfig:
        volume: float = 1.0
        length_scale: float = 1.0

    piper.PiperVoice = PiperVoice
    piper.SynthesisConfig = SynthesisConfig
    audio = FakePyAudio()
    pyaudio = types.ModuleType("pyaudio")
    pyaudio.PyAudio = lambda: audio
    monkeypatch.setitem(sys.modules, "piper", piper)
    monkeypatch.setitem(sys.modules, "pyaudio", pyaudio)
    for name in ("id_ID-news_tts-medium", "en_US-lessac-medium"):
        (tmp_path / f"{name}.onnx").write_bytes(b"model")
    return tmp_path, audio


VOICES = {"id": "id_ID-news_tts-medium", "en": "en_US-lessac-medium"}


def make(model_dir, language="id", voices=VOICES):
    return PiperTTS(voices=voices, model_dir=model_dir, language=language, volume=0.8, length_scale=1.1)


def test_voice_urls():
    model, config = voice_urls("id_ID-news_tts-medium")
    assert model == (
        "https://huggingface.co/rhasspy/piper-voices/resolve/main/id/id_ID/news_tts/medium/id_ID-news_tts-medium.onnx"
    )
    assert config == model + ".json"
    with pytest.raises(ValueError):
        voice_urls("not-a-valid-voice-name")


def test_speaks_every_sentence_with_config(fakes):
    model_dir, audio = fakes
    tts = make(model_dir)
    tts.speak("Satu. Dua.")
    stream = audio.streams[0]
    assert stream.rate == RATE
    assert stream.written == 2 * int(RATE * 0.2) * 2  # 2 sentences, 16-bit mono
    voice = tts._loaded["id"]
    assert voice.calls[0][1].volume == 0.8 and voice.calls[0][1].length_scale == 1.1
    tts.close()
    assert audio.terminated


def test_interrupt_stops_quickly(fakes):
    model_dir, audio = fakes
    tts = make(model_dir)
    text = ". ".join(f"Kalimat {i}" for i in range(20))  # ~4 s of audio
    worker = threading.Thread(target=tts.speak, args=(text,))
    started = time.monotonic()
    worker.start()
    time.sleep(0.15)
    tts.interrupt()
    worker.join(2)
    assert not worker.is_alive()
    assert time.monotonic() - started < 0.6
    assert audio.streams[0].written < 20 * int(RATE * 0.2) * 2
    # Later utterances are not affected by the earlier interrupt.
    before = audio.streams[0].written
    tts.speak("Lanjut.")
    assert audio.streams[0].written == before + int(RATE * 0.2) * 2
    tts.close()


def test_language_switch_and_missing_voice(fakes):
    model_dir, _ = fakes
    tts = make(model_dir)
    assert tts.set_language("en") is True
    assert tts.voice_found == {"id": True, "en": True}
    (model_dir / "en_US-lessac-medium.onnx").unlink()
    tts._loaded.pop("en")
    assert tts.set_language("en") is False
    assert tts.voice_found["en"] is False
    tts.close()


def test_missing_model_for_start_language_is_reported(fakes):
    model_dir, _ = fakes
    with pytest.raises(ComponentUnavailable, match="download-voices"):
        make(model_dir, voices={"id": "id_ID-other-medium", "en": "en_US-lessac-medium"})


def test_missing_library_is_reported(monkeypatch, tmp_path):
    monkeypatch.setitem(sys.modules, "piper", None)
    with pytest.raises(ComponentUnavailable, match="piper-tts"):
        make(tmp_path)


class FakeResponse:
    def __init__(self, payload, status=200):
        self.payload, self.status_code = payload, status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def iter_content(self, chunk_size):
        yield self.payload


class FakeSession:
    def __init__(self, status=200):
        self.urls = []
        self.status = status

    def get(self, url, stream, timeout):
        self.urls.append(url)
        return FakeResponse(b"data:" + url.encode(), self.status)


def test_download_voice_writes_files_and_skips_existing(tmp_path):
    session = FakeSession()
    path = download_voice("id_ID-news_tts-medium", tmp_path / "piper", session=session)
    assert path.read_bytes().endswith(b".onnx")
    assert (tmp_path / "piper" / "id_ID-news_tts-medium.onnx.json").exists()
    assert not list((tmp_path / "piper").glob("*.part"))
    assert len(session.urls) == 2
    download_voice("id_ID-news_tts-medium", tmp_path / "piper", session=session)
    assert len(session.urls) == 2  # nothing downloaded again


def test_failed_download_leaves_no_model(tmp_path):
    with pytest.raises(RuntimeError):
        download_voice("id_ID-news_tts-medium", tmp_path, session=FakeSession(status=404))
    assert not (tmp_path / "id_ID-news_tts-medium.onnx").exists()


def test_auto_engine_falls_back_to_pyttsx3(monkeypatch):
    from aiforus import cli
    from aiforus.hal import piper_tts, tts

    def no_piper(**kwargs):
        raise ComponentUnavailable("piper-tts is not installed")

    sentinel = object()
    monkeypatch.setattr(piper_tts, "PiperTTS", no_piper)
    monkeypatch.setattr(tts, "Pyttsx3TTS", lambda **kwargs: sentinel)
    components = cli.Components()
    assert cli._build_voice(components, Settings(), "id") is sentinel
    assert components.status["voice output (piper)"].startswith("unavailable")

    forced = Settings.model_validate({"speech": {"engine": "piper"}})
    assert cli._build_voice(cli.Components(), forced, "id") is None
