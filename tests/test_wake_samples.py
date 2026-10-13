import wave

import numpy as np

from aiforus.hal.listening import FRAME_SAMPLES
from aiforus.wake_samples import record_samples


class Mic:
    def __init__(self):
        self.reads = 0
        self.drains = 0

    def read(self):
        self.reads += 1
        return np.full(FRAME_SAMPLES, 1000, dtype="<i2").tobytes()

    def drain(self):
        self.drains += 1


def test_records_clips_per_phrase_and_continues_numbering(tmp_path):
    mic, beeps, prompts = Mic(), [], []
    answers = iter(["", "s", ""])
    saved = record_samples(
        mic,
        tmp_path,
        count=2,
        phrases={"hai_nemo": "hai nemo", "nemo": "nemo", "tolong": "tolong"},
        ask=lambda prompt: (prompts.append(prompt), next(answers))[1],
        say=lambda text: None,
        beep=lambda: beeps.append(1),
    )
    assert saved == {"hai_nemo": 2, "tolong": 2}
    files = sorted(p.name for p in (tmp_path / "hai_nemo").glob("*.wav"))
    assert files == ["hai_nemo_001.wav", "hai_nemo_002.wav"]
    with wave.open(str(tmp_path / "tolong" / "tolong_001.wav")) as wav:
        assert (wav.getframerate(), wav.getnchannels(), wav.getsampwidth()) == (16000, 1, 2)
        assert wav.getnframes() == 25 * FRAME_SAMPLES  # 2 s
    assert len(beeps) == mic.drains == 4

    record_samples(
        mic, tmp_path, count=1, phrases={"hai_nemo": "hai nemo"}, ask=lambda p: "", say=lambda t: None
    )
    assert (tmp_path / "hai_nemo" / "hai_nemo_003.wav").exists()


def test_q_stops(tmp_path):
    saved = record_samples(Mic(), tmp_path, count=1, ask=lambda p: "q", say=lambda t: None)
    assert saved == {}
