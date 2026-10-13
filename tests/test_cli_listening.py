import types

import pytest

from aiforus import cli
from aiforus.config import Settings
from aiforus.hal import ComponentUnavailable


class Dummy:
    def __init__(self, *args, **kwargs):
        self.args, self.kwargs = args, kwargs
        self.name = "vosk"
        self.label = "space"


def unavailable(*args, **kwargs):
    raise ComponentUnavailable("not here")


@pytest.fixture
def hal(monkeypatch):
    import aiforus.hal.listening as listening
    import aiforus.hal.stt as stt

    for name in (
        "PyAudioSource",
        "GoogleTranscriber",
        "ConsoleKey",
        "VoskWakeDetector",
        "OpenWakeWordDetector",
    ):
        monkeypatch.setattr(listening, name, Dummy)
    monkeypatch.setattr(stt, "GoogleSpeechInput", Dummy)
    return listening


def build(**listening):
    settings = Settings.model_validate({"listening": listening})
    c = cli.Components()
    return cli._build_listener(c, settings, "id"), c.status


def test_wake_word_and_key(hal):
    listener, status = build()
    assert isinstance(listener, hal.TriggeredSpeechInput)
    assert listener.detector is not None and listener.key is not None
    assert status[cli._LISTENING].startswith("wake word 'Hai Nemo' (vosk) + push-to-talk [space]")


def test_push_to_talk_only(hal):
    listener, status = build(mode="push_to_talk")
    assert listener.detector is None and listener.key is not None


def test_always_keeps_the_old_listener(hal):
    listener, status = build(mode="always")
    assert isinstance(listener, Dummy)
    assert status[cli._LISTENING].startswith("always")


def test_wake_word_unavailable_falls_back_to_the_key(hal, monkeypatch):
    monkeypatch.setattr(hal, "VoskWakeDetector", unavailable)
    listener, status = build()
    assert listener.detector is None and listener.key is not None
    assert "unavailable" in status["wake word (vosk)"]


def test_nothing_available_falls_back_to_always(hal, monkeypatch):
    monkeypatch.setattr(hal, "VoskWakeDetector", unavailable)
    monkeypatch.setattr(hal, "ConsoleKey", unavailable)
    listener, status = build()
    assert isinstance(listener, Dummy)
    assert "fallback" in status[cli._LISTENING]


def test_vosk_detector_gets_name_greetings_and_help(hal):
    listener, _ = build()
    kwargs = listener.detector.kwargs
    assert kwargs["names"] == ["Nemo"] and "hello" in kwargs["greetings"]
    assert kwargs["emergency_phrases"] == ["help", "help me", "help help"]
    listener, _ = build(emergency_without_name=False)
    assert listener.detector.kwargs["emergency_phrases"] == []


def test_openwakeword_models_from_the_model_dir(hal):
    listener, status = build(wake_engine="openwakeword")
    wake, emergency = listener.detector.args
    assert wake.name == "hai_nemo.onnx" and wake.parent.name == "wakeword"
    assert emergency.name == "tolong.onnx"


def test_listening_mode_names():
    from aiforus.hal.stt import KeyboardInput

    assert cli._listening_mode(KeyboardInput()) == "text"
    assert cli._listening_mode(types.SimpleNamespace()) == "always"
