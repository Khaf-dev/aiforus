"""Record real voice samples for training the wake word models.

``python -m aiforus --record-wake-samples`` asks you to say each phrase a
number of times and saves 2-second clips (16 kHz mono WAV) to
``data/wake_samples/<phrase>/``. Synthetic training voices are English, so a
few dozen real Indonesian recordings make "hai nemo" and "tolong" much more
reliable. Recordings stay on this machine; you upload them to Colab yourself
(see tools/wakeword/README.md). Ask before recording someone else.
"""

from __future__ import annotations

import wave
from collections.abc import Callable
from pathlib import Path

from .hal.listening import FRAME_S, SAMPLE_RATE, AudioSource

PHRASES = {
    "hai_nemo": "hai nemo",
    "halo_nemo": "halo nemo",
    "nemo": "nemo",
    "tolong": "tolong",
    "darurat": "darurat",
}
CLIP_S = 2.0


def write_wav(path: Path, pcm: bytes, sample_rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(pcm)


def record_clip(source: AudioSource, seconds: float = CLIP_S) -> bytes:
    return b"".join(source.read() for _ in range(round(seconds / FRAME_S)))


def record_samples(
    source: AudioSource,
    out_dir: Path,
    *,
    count: int = 20,
    phrases: dict[str, str] | None = None,
    ask: Callable[[str], str] = input,
    say: Callable[[str], object] = print,
    beep: Callable[[], object] = lambda: None,
) -> dict[str, int]:
    """Record ``count`` clips per phrase; returns how many were saved each.

    Typing ``s`` skips a phrase, ``q`` stops. Numbering continues after
    existing files, so you can add more later (other people, other rooms).
    """
    saved: dict[str, int] = {}
    for slug, phrase in (phrases or PHRASES).items():
        folder = out_dir / slug
        start = len(list(folder.glob("*.wav"))) if folder.exists() else 0
        answer = (
            ask(f"\n'{phrase}': {count} rekaman. Enter = mulai, s = lewati, q = selesai > ").strip().lower()
        )
        if answer == "q":
            break
        if answer == "s":
            continue
        saved[slug] = 0
        for i in range(count):
            say(f"  [{i + 1}/{count}] ucapkan: {phrase}")
            beep()
            drain = getattr(source, "drain", None)
            if drain is not None:
                drain()  # audio buffered while waiting (and the beep) is not part of the clip
            pcm = record_clip(source)
            write_wav(folder / f"{slug}_{start + i + 1:03d}.wav", pcm)
            saved[slug] += 1
    return saved
