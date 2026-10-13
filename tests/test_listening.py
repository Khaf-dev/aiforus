import json
import sys
import types
import zipfile

import numpy as np
import pytest

from aiforus.hal import ComponentUnavailable
from aiforus.hal.listening import (
    FRAME_SAMPLES,
    CommandRecorder,
    OpenWakeWordDetector,
    Trigger,
    TriggeredSpeechInput,
    VoskWakeDetector,
    beep_pcm,
    classify_keywords,
)

SILENT = np.zeros(FRAME_SAMPLES, dtype="<i2").tobytes()
LOUD = (np.sin(np.arange(FRAME_SAMPLES) / 3) * 6000).astype("<i2").tobytes()


class Script:
    """Feeds frames; when they run out the listener is closed (ends listen())."""

    def __init__(self, frames):
        self.frames = list(frames)
        self.read_count = 0
        self.listener = None
        self.closed = False

    def read(self):
        self.read_count += 1
        if not self.frames:
            self.listener.closed = True
            return SILENT
        return self.frames.pop(0)

    def close(self):
        self.closed = True


class FakeDetector:
    name = "fake"
    emergency_is_standalone = True

    def __init__(self, at=None):
        self.at = dict(at or {})  # frame number -> Trigger
        self.n = 0
        self.resets = 0

    def process(self, frame):
        self.n += 1
        return self.at.get(self.n)

    def reset(self):
        self.resets += 1


class FakeKey:
    label = "space"

    def __init__(self, press_at=()):
        self.press_at = set(press_at)
        self.n = 0

    def pressed(self):
        self.n += 1
        return self.n in self.press_at


class FakeTranscriber:
    def __init__(self, text="apa di depan"):
        self.text = text
        self.audio = []

    def transcribe(self, pcm, sample_rate, language):
        self.audio.append((len(pcm) // 2 // FRAME_SAMPLES, sample_rate, language))
        return self.text


def make(frames, *, detector=None, key=None, speaking=lambda: False, **kwargs):
    source = Script(frames)
    transcriber = FakeTranscriber()
    listener = TriggeredSpeechInput(
        source,
        transcriber,
        language="id",
        detector=detector,
        key=key,
        recorder=CommandRecorder(start_timeout_s=0.5, max_s=3.0, end_silence_s=0.24),
        **kwargs,
    )
    listener.ECHO_GUARD_S = 0.0
    source.listener = listener
    triggers = []
    listener.attach(on_trigger=triggers.append, is_speaking=speaking)
    return listener, transcriber, triggers


def test_wake_word_records_one_command_and_transcribes_it():
    frames = [SILENT] * 3 + [LOUD] * 5 + [SILENT] * 6
    detector = FakeDetector({3: Trigger.WAKE})
    listener, transcriber, triggers = make(frames, detector=detector)
    assert listener.listen() == "apa di depan"
    assert triggers == [Trigger.WAKE]
    frames_sent, rate, language = transcriber.audio[0]
    assert rate == 16000 and language == "id"
    assert 5 <= frames_sent <= 3 + 5 + 3  # lead-in + speech + trailing silence, not the idle time
    assert detector.resets == 1


def test_nothing_is_transcribed_without_the_wake_word_or_key():
    frames = [LOUD] * 20 + [SILENT] * 5
    listener, transcriber, triggers = make(frames, detector=FakeDetector())
    assert listener.listen() is None
    assert transcriber.audio == [] and triggers == []


def test_no_speech_after_the_wake_word_returns_none():
    listener, transcriber, _ = make([SILENT] * 30, detector=FakeDetector({2: Trigger.WAKE}))
    assert listener.listen() is None
    assert transcriber.audio == []


def test_key_interrupts_even_while_the_assistant_speaks():
    frames = [SILENT] * 2 + [LOUD] * 4 + [SILENT] * 6
    listener, transcriber, triggers = make(frames, key=FakeKey(press_at={2}), speaking=lambda: True)
    assert listener.listen() == "apa di depan"
    assert triggers == [Trigger.KEY]


def test_own_voice_cannot_wake_the_assistant_without_a_headset():
    frames = [LOUD] * 6 + [SILENT] * 3
    detector = FakeDetector({1: Trigger.WAKE, 2: Trigger.WAKE})
    listener, _, triggers = make(frames, detector=detector, speaking=lambda: True)
    assert listener.listen() is None
    assert triggers == [] and detector.n == 0  # not even fed to the detector


def test_with_a_headset_the_name_interrupts_too():
    frames = [SILENT] + [LOUD] * 4 + [SILENT] * 6
    detector = FakeDetector({1: Trigger.WAKE})
    listener, _, triggers = make(frames, detector=detector, speaking=lambda: True, headset=True)
    assert listener.listen() == "apa di depan"
    assert triggers == [Trigger.WAKE]


def test_echo_guard_after_speaking():
    speaking = iter([True, False, False, False])
    frames = [SILENT] * 4 + [SILENT] * 3
    detector = FakeDetector({1: Trigger.WAKE})
    listener, _, triggers = make(frames, detector=detector, speaking=lambda: next(speaking, False))
    listener.ECHO_GUARD_S = 60.0
    assert listener.listen() is None and triggers == []


@pytest.mark.parametrize("language, text", [("id", "darurat"), ("en", "emergency")])
def test_emergency_word_without_the_name(language, text):
    listener, transcriber, triggers = make([SILENT] * 3, detector=FakeDetector({2: Trigger.EMERGENCY}))
    listener.set_language(language)
    assert listener.listen() == text
    assert triggers == [Trigger.EMERGENCY]
    assert transcriber.audio == []  # handled locally, nothing sent anywhere


def test_emergency_without_name_can_be_switched_off():
    listener, _, triggers = make([SILENT] * 4, detector=FakeDetector({2: Trigger.EMERGENCY}), emergency=False)
    assert listener.listen() is None and triggers == []


def test_needs_a_detector_or_a_key():
    with pytest.raises(ValueError):
        TriggeredSpeechInput(Script([]), FakeTranscriber(), language="id")


def test_recorder_stops_at_the_length_limit():
    recorder = CommandRecorder(start_timeout_s=1, max_s=0.8, end_silence_s=1)
    audio = recorder.record(iter([LOUD] * 50), noise_rms=100)
    assert len(audio) // 2 // FRAME_SAMPLES == 10  # 0.8 s


@pytest.mark.parametrize(
    "text, final, expected",
    [
        ("hi nemo", False, Trigger.WAKE),
        ("[unk] nemo", False, Trigger.WAKE),
        ("help", True, Trigger.EMERGENCY),
        ("help me", True, Trigger.EMERGENCY),
        ("help", False, None),  # wait for the end of the utterance
        ("help [unk]", True, None),  # "help me with this" is not an emergency
        ("[unk] [unk]", True, None),
        ("", True, None),
    ],
)
def test_keyword_classification(text, final, expected):
    assert classify_keywords(text, {"nemo"}, {"help", "help me"}, final=final) is expected


def test_beep_is_short_and_not_clipped():
    samples = np.frombuffer(beep_pcm(), dtype="<i2")
    assert 0.1 < samples.size / 16000 < 0.2
    assert np.abs(samples).max() < 32767 * 0.5
    assert abs(int(samples[0])) < 200 and abs(int(samples[-1])) < 200  # soft edges, no click


# -- engines (with fake libraries) ------------------------------------------------


class FakeKaldi:
    def __init__(self, model, rate, grammar):
        self.grammar = json.loads(grammar)
        self.results = list(model.results)

    def AcceptWaveform(self, frame):  # noqa: N802 - Vosk API
        self.current = self.results.pop(0) if self.results else ("partial", "")
        return self.current[0] == "final"

    def Result(self):  # noqa: N802 - Vosk API
        return json.dumps({"text": self.current[1]})

    def PartialResult(self):  # noqa: N802 - Vosk API
        return json.dumps({"partial": self.current[1]})


@pytest.fixture
def fake_vosk(monkeypatch, tmp_path):
    state = {"vocab": {"nemo", "hi", "hey", "hello", "help", "me"}, "results": []}

    class Model:
        def __init__(self, path):
            self.results = state["results"]

        def vosk_model_find_word(self, word):  # the real vosk method name
            return 1 if word in state["vocab"] else -1

    module = types.SimpleNamespace(Model=Model, KaldiRecognizer=FakeKaldi, SetLogLevel=lambda level: None)
    monkeypatch.setitem(sys.modules, "vosk", module)
    (tmp_path / "vosk-model").mkdir()
    return state, tmp_path / "vosk-model"


def test_vosk_detector_grammar_and_triggers(fake_vosk):
    state, model_dir = fake_vosk
    state["results"] = [("partial", "hi"), ("partial", "hi nemo"), ("final", "help")]
    detector = VoskWakeDetector(
        model_dir, names=["Nemo"], greetings=["hi", "hello"], emergency_phrases=["help", "tolong"]
    )
    grammar = detector._recognizer.grammar
    assert {"nemo", "hi nemo", "hello nemo", "help", "[unk]"} <= set(grammar)
    assert "tolong" not in grammar  # not in the English vocabulary: skipped, not silently broken
    assert [detector.process(SILENT) for _ in range(3)] == [None, Trigger.WAKE, Trigger.EMERGENCY]


def test_vosk_detector_refuses_a_name_it_cannot_hear(fake_vosk):
    _, model_dir = fake_vosk
    with pytest.raises(ComponentUnavailable, match="doesn't know"):
        VoskWakeDetector(model_dir, names=["Sinta"], greetings=[], emergency_phrases=[])


def test_vosk_detector_needs_the_model(fake_vosk, tmp_path):
    with pytest.raises(ComponentUnavailable, match="download-models"):
        VoskWakeDetector(tmp_path / "missing", names=["Nemo"], greetings=[], emergency_phrases=[])


def test_openwakeword_detector(monkeypatch, tmp_path):
    scores = iter([{"hai_nemo": 0.1, "tolong": 0.2}, {"hai_nemo": 0.9}, {"tolong": 0.7, "hai_nemo": 0.8}])

    class Model:
        def __init__(self, wakeword_models, inference_framework):
            self.paths = wakeword_models
            assert inference_framework == "onnx"

        def predict(self, samples):
            assert samples.dtype == np.dtype("<i2") and samples.size == FRAME_SAMPLES
            return next(scores)

        def reset(self):
            pass

    monkeypatch.setitem(sys.modules, "openwakeword", types.ModuleType("openwakeword"))
    monkeypatch.setitem(sys.modules, "openwakeword.model", types.SimpleNamespace(Model=Model))
    wake, emergency = tmp_path / "hai_nemo.onnx", tmp_path / "tolong.onnx"
    with pytest.raises(ComponentUnavailable, match="tools/wakeword"):
        OpenWakeWordDetector(wake, emergency)
    wake.write_bytes(b"onnx")
    emergency.write_bytes(b"onnx")
    detector = OpenWakeWordDetector(wake, emergency, threshold=0.5)
    assert detector.listens_for_emergency
    # emergency wins when both fire
    assert [detector.process(SILENT) for _ in range(3)] == [None, Trigger.WAKE, Trigger.EMERGENCY]


# -- zip download for the Vosk model ------------------------------------------------


class _Response:
    def __init__(self, data):
        self.data = data

    def raise_for_status(self):
        pass

    def iter_content(self, chunk_size):
        yield self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class _Session:
    def __init__(self, data):
        self.data, self.calls = data, 0

    def get(self, url, stream, timeout):
        self.calls += 1
        return _Response(self.data)


def _zip_bytes(tmp_path, members):
    path = tmp_path / "src.zip"
    with zipfile.ZipFile(path, "w") as zf:
        for name, content in members.items():
            zf.writestr(name, content)
    return path.read_bytes()


def test_download_and_extract_zip(tmp_path):
    from aiforus.downloads import download_and_extract_zip

    session = _Session(_zip_bytes(tmp_path, {"model-x/am/final.mdl": "x", "model-x/conf/model.conf": "y"}))
    target = download_and_extract_zip(
        "https://example/model-x.zip", tmp_path / "vosk", "model-x", session=session
    )
    assert (target / "am" / "final.mdl").read_text() == "x"
    assert not (tmp_path / "vosk" / "model-x.zip").exists()
    download_and_extract_zip("https://example/model-x.zip", tmp_path / "vosk", "model-x", session=session)
    assert session.calls == 1  # already there: no second download


def test_download_and_extract_zip_refuses_paths_outside_the_folder(tmp_path):
    from aiforus.downloads import download_and_extract_zip

    session = _Session(_zip_bytes(tmp_path, {"../evil.txt": "x"}))
    with pytest.raises(ValueError, match="Unsafe path"):
        download_and_extract_zip("https://example/m.zip", tmp_path / "vosk", "m", session=session)
    assert not (tmp_path / "evil.txt").exists()


def test_frame_based_emergency_needs_silence_after_it():
    """openWakeWord can fire on "tolong" inside "tolong ambilkan air"."""
    detector = FakeDetector({2: Trigger.EMERGENCY})
    detector.emergency_is_standalone = False
    listener, _, triggers = make([SILENT] * 2 + [LOUD] * 12 + [SILENT] * 3, detector=detector)
    assert listener.listen() is None and triggers == []

    detector = FakeDetector({2: Trigger.EMERGENCY})
    detector.emergency_is_standalone = False
    listener, _, triggers = make([SILENT] * 2 + [LOUD] * 2 + [SILENT] * 14, detector=detector)
    assert listener.listen() == "darurat" and triggers == [Trigger.EMERGENCY]
