import sys
import threading
import time
import types

import pytest

from aiforus.hal.location import IpLocationProvider


class _Voice:
    def __init__(self, id_, name, languages=()):
        self.id, self.name, self.languages = id_, name, list(languages)


class _FakeEngine:
    """Mimics pyttsx3: runAndWait() fires started-word per word."""

    def __init__(self):
        self.props = {
            "voices": [
                _Voice("HKEY\\TTS_MS_EN-US_ZIRA", "Microsoft Zira Desktop"),
                _Voice("HKEY\\TTS_MS_ID-ID_ANDIKA", "Microsoft Andika"),
            ]
        }
        self.callbacks = {}
        self.pending = []
        self.words_spoken = []
        self._stopped = False

    def setProperty(self, key, value):  # noqa: N802 - pyttsx3 API
        self.props[key] = value

    def getProperty(self, key):  # noqa: N802 - pyttsx3 API
        return self.props.get(key)

    def connect(self, topic, cb):
        self.callbacks[topic] = cb

    def say(self, text):
        self.pending.append(text)

    def stop(self):
        self._stopped = True

    def runAndWait(self):  # noqa: N802 - pyttsx3 API
        self._stopped = False
        for text in self.pending:
            for word in text.split():
                self.callbacks["started-word"]("utt", 0, len(word))
                if self._stopped:
                    self.pending = []
                    return
                self.words_spoken.append(word)
                time.sleep(0.01)
        self.pending = []


@pytest.fixture
def fake_pyttsx3(monkeypatch):
    engine = _FakeEngine()
    module = types.ModuleType("pyttsx3")
    module.init = lambda: engine
    monkeypatch.setitem(sys.modules, "pyttsx3", module)
    return engine


def _make_tts(language="id"):
    from aiforus.hal.tts import Pyttsx3TTS

    return Pyttsx3TTS(
        rate=170,
        volume=1.0,
        voice_hints={"id": ["andika", "id-id"], "en": ["zira"], "ja": ["haruka"]},
        language=language,
    )


def test_pyttsx3_picks_voice_by_language(fake_pyttsx3):
    tts = _make_tts("id")
    assert fake_pyttsx3.props["voice"].endswith("ANDIKA")
    assert tts.set_language("en") is True
    assert fake_pyttsx3.props["voice"].endswith("ZIRA")
    assert tts.set_language("ja") is False
    tts.close()


def test_pyttsx3_speaks_full_text(fake_pyttsx3):
    tts = _make_tts()
    tts.speak("satu dua tiga")
    assert fake_pyttsx3.words_spoken == ["satu", "dua", "tiga"]
    tts.close()


def test_pyttsx3_interrupt_cuts_speech_short(fake_pyttsx3):
    tts = _make_tts()
    words = " ".join(f"kata{i}" for i in range(200))  # ~2 s of fake speech
    worker = threading.Thread(target=tts.speak, args=(words,))
    started = time.monotonic()
    worker.start()
    time.sleep(0.05)
    tts.interrupt()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert time.monotonic() - started < 1.0
    assert 0 < len(fake_pyttsx3.words_spoken) < 200
    # The engine keeps working after an interrupt.
    fake_pyttsx3.words_spoken.clear()
    tts.speak("lanjut")
    assert fake_pyttsx3.words_spoken == ["lanjut"]
    tts.close()


def test_pyttsx3_missing_library_is_reported(monkeypatch):
    from aiforus.hal import ComponentUnavailable

    monkeypatch.setitem(sys.modules, "pyttsx3", None)
    with pytest.raises(ComponentUnavailable):
        _make_tts()


class _Resp:
    def __init__(self, payload, status=200):
        self._payload, self.status_code = payload, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return self._payload


class _Session:
    def __init__(self, response=None, exc=None):
        self.headers = {}
        self.response, self.exc = response, exc
        self.calls = []

    def get(self, url, timeout):
        self.calls.append((url, timeout))
        if self.exc:
            raise self.exc
        return self.response


def test_ip_location_parses_and_is_marked_approximate():
    session = _Session(_Resp({"loc": "-6.2,106.8", "city": "Jakarta", "country": "ID"}))
    provider = IpLocationProvider("https://ipinfo.test/json", 3, "ua", session=session)
    loc = provider.locate()
    assert (loc.latitude, loc.longitude) == (-6.2, 106.8)
    assert loc.label == "Jakarta, ID"
    assert loc.is_approximate
    assert session.calls == [("https://ipinfo.test/json", 3)]
    assert session.headers["User-Agent"] == "ua"


@pytest.mark.parametrize(
    "session",
    [_Session(exc=OSError("offline")), _Session(_Resp({}, 500)), _Session(_Resp({"city": "x"}))],
)
def test_ip_location_failures_return_none(session):
    assert IpLocationProvider("u", 1, "ua", session=session).locate() is None
