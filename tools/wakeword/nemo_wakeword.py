"""Helpers for training the "Hai Nemo" and "Tolong" wake word models.

This file runs on Google Colab (openWakeWord training is Linux-only); the
notebook ``train_nemo.ipynb`` writes it to disk with ``%%writefile`` and the
tests in ``tests/test_wakeword_tools.py`` import it here. It only needs numpy
and scipy, plus openwakeword for :func:`score_wavs`.

What it adds to the standard openWakeWord recipe:

* **presets** for the two AIForUs models: phrases, phonetic spellings that make
  the English training voices sound closer to Indonesian, and look-alike words
  that must *not* trigger;
* **real recordings** from ``python -m aiforus --record-wake-samples``: trimmed,
  resampled to 16 kHz and mixed into the synthetic training clips, with a part
  held back to check the finished model on real voices.
"""

from __future__ import annotations

import random
import shutil
import wave
import zipfile
from dataclasses import dataclass
from math import gcd
from pathlib import Path

import numpy as np

SAMPLE_RATE = 16000


@dataclass(frozen=True)
class Preset:
    model_name: str
    target_phrase: tuple[str, ...]
    negative_phrases: tuple[str, ...]
    sample_folders: tuple[str, ...]  # data/wake_samples/<folder> from the recorder


PRESETS: dict[str, Preset] = {
    # The model file name is what AIForUs loads: listening.openwakeword_wake_model.
    "hai_nemo": Preset(
        model_name="hai_nemo",
        target_phrase=(
            "hi nemo",
            "hey nemo",
            "hello nemo",
            "nemo",
            # Phonetic spellings: Indonesian "Nemo" is "neh-moh", not "nee-moh".
            "hi neh moh",
            "hah lo neh moh",
            "neh moh",
        ),
        negative_phrases=(
            "demo",
            "memo",
            "emo",
            "nemu",
            "nenek",
            "lemon",
            "nomor",
            "nama",
            "enam",
            "hi demo",
            "hello memo",
            "hey emo",
            "hai lemon",
            "nanti",
            "ne mau",
        ),
        sample_folders=("hai_nemo", "halo_nemo", "nemo"),
    ),
    "tolong": Preset(
        model_name="tolong",
        target_phrase=(
            "tolong",
            "toh long",
            "toe long",
            "tolong tolong",
            "darurat",
            "dah roo raht",
        ),
        negative_phrases=(
            "tulang",
            "potong",
            "gotong",
            "kolong",
            "dorong",
            "sarung",
            "belong",
            "along",
            "darat",
            "darah",
            "durian",
            "the long",
            "too long",
        ),
        sample_folders=("tolong", "darurat"),
    ),
}

SIZES = {
    # n_samples, n_samples_val, steps. "small" is a first try; "full" is the
    # size the openWakeWord docs recommend for a model you rely on.
    "small": (3000, 1000, 15000),
    "full": (10000, 2000, 50000),
}


def make_config(base: dict, preset: Preset, *, size: str = "small", **paths: object) -> dict:
    """The openWakeWord training config for ``preset``, based on the repo's
    ``examples/custom_model.yml`` (``base``). ``paths`` overrides keys such as
    ``output_dir`` or ``background_paths``."""
    n_samples, n_samples_val, steps = SIZES[size]
    config = dict(base)
    config.update(
        model_name=preset.model_name,
        target_phrase=list(preset.target_phrase),
        custom_negative_phrases=list(preset.negative_phrases),
        n_samples=n_samples,
        n_samples_val=n_samples_val,
        steps=steps,
    )
    config.update(paths)
    return config


# -- real recordings -------------------------------------------------------------


def read_wav(path: Path) -> tuple[np.ndarray, int]:
    """16-bit PCM WAV -> (float32 mono in -1..1, sample rate)."""
    with wave.open(str(path), "rb") as wav:
        if wav.getsampwidth() != 2:
            raise ValueError(f"{path.name}: only 16-bit WAV is supported")
        rate = wav.getframerate()
        channels = wav.getnchannels()
        data = np.frombuffer(wav.readframes(wav.getnframes()), dtype="<i2").astype(np.float32)
    if channels > 1:
        data = data.reshape(-1, channels).mean(axis=1)
    return data / 32768.0, rate


def write_wav(path: Path, audio: np.ndarray, rate: int = SAMPLE_RATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pcm = (np.clip(audio, -1.0, 1.0) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        wav.writeframes(pcm.tobytes())


def resample(audio: np.ndarray, rate: int, target: int = SAMPLE_RATE) -> np.ndarray:
    if rate == target:
        return audio
    from scipy.signal import resample_poly

    g = gcd(rate, target)
    return resample_poly(audio, target // g, rate // g).astype(np.float32)


def trim_silence(
    audio: np.ndarray, rate: int = SAMPLE_RATE, *, frame_s: float = 0.02, margin_s: float = 0.1
) -> np.ndarray:
    """Cut the quiet parts before and after the phrase.

    openWakeWord places each training clip near the *end* of its window, so a
    recording that ends with a second of silence would teach the model that
    the phrase ends a second before the window does. Returns an empty array
    when nothing stands out from the background (a failed recording).
    """
    frame = max(1, int(rate * frame_s))
    n = len(audio) // frame
    if n == 0:
        return audio[:0]
    energy = np.sqrt(np.mean(audio[: n * frame].reshape(n, frame) ** 2, axis=1))
    floor = float(np.percentile(energy, 10))
    peak = float(energy.max())
    if peak < 0.01 or peak < floor * 4:
        return audio[:0]
    threshold = max(floor * 3, peak * 0.1)
    loud = np.flatnonzero(energy > threshold)
    margin = int(rate * margin_s)
    start = max(0, loud[0] * frame - margin)
    end = min(len(audio), (loud[-1] + 1) * frame + margin)
    return audio[start:end]


def unpack_samples(source: Path, dest: Path) -> Path:
    """Unzip ``wake_samples.zip`` (or use a folder as is). Returns the folder
    that contains the phrase folders (hai_nemo/, tolong/, ...)."""
    source = Path(source)
    if source.is_dir():
        root = source
    else:
        dest.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(source) as archive:
            for member in archive.namelist():
                target = (dest / member).resolve()
                if not target.is_relative_to(dest.resolve()):
                    raise ValueError(f"unsafe path in zip: {member}")
            archive.extractall(dest)
        root = dest
    # The zip may contain "wake_samples/hai_nemo/..." or "hai_nemo/..." directly.
    for candidate in (root, *sorted(p for p in root.iterdir() if p.is_dir())):
        if any((candidate / name).is_dir() for preset in PRESETS.values() for name in preset.sample_folders):
            return candidate
    raise FileNotFoundError(f"no phrase folders (hai_nemo/, tolong/, ...) in {source}")


@dataclass
class RealClips:
    train: list[Path]
    held_out: list[Path]
    skipped: list[Path]


def prepare_real_clips(
    samples_root: Path, preset: Preset, out_dir: Path, *, hold_out: float = 0.2, seed: int = 0
) -> RealClips:
    """Trim and resample the real recordings for ``preset`` into ``out_dir``.

    A share (``hold_out``) is kept out of training so the finished model can
    be checked on voices it has never heard.
    """
    clips: list[Path] = []
    skipped: list[Path] = []
    for folder in preset.sample_folders:
        for path in sorted((samples_root / folder).glob("*.wav")):
            audio, rate = read_wav(path)
            audio = trim_silence(resample(audio, rate))
            if len(audio) < SAMPLE_RATE * 0.2:  # silence or a click
                skipped.append(path)
                continue
            target = out_dir / folder / path.name
            write_wav(target, audio)
            clips.append(target)
    random.Random(seed).shuffle(clips)
    n_held = round(len(clips) * hold_out) if len(clips) >= 5 else 0
    return RealClips(train=clips[n_held:], held_out=clips[:n_held], skipped=skipped)


def add_to_training(
    clips: list[Path], positive_train_dir: Path, *, n_synthetic: int, share: float = 0.2
) -> int:
    """Copy real clips into openWakeWord's ``positive_train`` folder.

    Call this *after* ``train.py --generate_clips`` (otherwise it generates
    fewer synthetic clips) and *before* ``--augment_clips``. Each clip is copied
    several times so real voices make up about ``share`` of the positives; the
    augmentation step gives every copy different noise and room echo.
    Returns the number of files added.
    """
    if not clips:
        return 0
    copies = max(1, round(n_synthetic * share / (1 - share) / len(clips)))
    positive_train_dir.mkdir(parents=True, exist_ok=True)
    added = 0
    for clip in clips:
        for i in range(copies):
            shutil.copyfile(clip, positive_train_dir / f"real_{clip.parent.name}_{clip.stem}_{i:03d}.wav")
            added += 1
    return added


# -- the whole recipe for one model ------------------------------------------------


# PyTorch 2.6+ refuses to unpickle the Piper and DeepPhonemizer checkpoints
# that train.py loads ("Weights only load failed"). This switches the old
# behaviour back for the training steps only; the Piper checkpoint is checked
# against a fixed SHA-256 by the notebook before it is ever loaded.
TRAIN_ENV = {"TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD": "1"}


def run(cmd: list[str], env: dict[str, str] | None = None) -> None:
    """Run a command and stream its output (a notebook does not show the output
    of a plain subprocess). Raises if it fails, so a broken step stops the run."""
    import os
    import subprocess

    print("$", " ".join(cmd), flush=True)
    full_env = {**os.environ, **(env or {})}
    with subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, env=full_env
    ) as proc:
        assert proc.stdout is not None
        for line in proc.stdout:
            print(line, end="", flush=True)
    if proc.returncode:
        raise RuntimeError(f"step failed (exit code {proc.returncode}): {' '.join(cmd)}")


# train.py declares --convert_to_tflite with default="False" - a non-empty
# string, so it always tries the TFLite conversion and crashes without the old
# TensorFlow 2.8 stack (which no longer installs on Colab). AIForUs only needs
# the ONNX model, so the check is made strict like the other flags.
_TFLITE_CHECK = "if args.convert_to_tflite:"
_TFLITE_FIXED = "if args.convert_to_tflite is True:"


def patch_train_script(train_script: Path) -> None:
    text = Path(train_script).read_text(encoding="utf-8")
    if _TFLITE_CHECK in text:
        Path(train_script).write_text(text.replace(_TFLITE_CHECK, _TFLITE_FIXED), encoding="utf-8")
    elif _TFLITE_FIXED not in text:
        raise RuntimeError(f"{train_script} changed upstream; check its --convert_to_tflite handling")


@dataclass
class TrainResult:
    model_path: Path
    real_added: int
    held_out: list[Path]
    skipped: list[Path]


def train_model(
    preset: Preset,
    *,
    base_config: dict,
    train_script: Path,
    work_dir: Path,
    size: str = "small",
    samples_root: Path | None = None,
    overrides: dict | None = None,
    runner=run,
) -> TrainResult:
    """openWakeWord's three steps, with the real recordings slipped in between
    generating and augmenting. Safe to re-run after a disconnect: clips that
    already exist are kept, and augmentation is redone unless it finished."""
    import sys

    import yaml

    patch_train_script(train_script)
    config = make_config(base_config, preset, size=size, **(overrides or {}))
    config_path = work_dir / f"{preset.model_name}.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    base = [sys.executable, str(train_script), "--training_config", str(config_path)]

    runner([*base, "--generate_clips"], TRAIN_ENV)

    real = RealClips([], [], [])
    added = 0
    if samples_root is not None:
        real = prepare_real_clips(samples_root, preset, work_dir / "real_clips" / preset.model_name)
        positive_train = Path(config["output_dir"]) / preset.model_name / "positive_train"
        n_synthetic = sum(1 for p in positive_train.glob("*.wav") if not p.name.startswith("real_"))
        added = sum(1 for _ in positive_train.glob("real_*.wav"))
        if not added:  # a re-run must not add them twice
            added = add_to_training(real.train, positive_train, n_synthetic=n_synthetic)
        print(
            f"Real recordings for '{preset.model_name}': {len(real.train)} for training "
            f"({added} copies), {len(real.held_out)} kept back for checking, "
            f"{len(real.skipped)} skipped (silent or failed)."
        )

    # train.py skips augmentation when the feature files exist - even half-written
    # ones from a run that was cut off. So it only counts as done once it finished.
    augmented = Path(config["output_dir"]) / preset.model_name / "augmented.done"
    if not augmented.exists():
        runner([*base, "--augment_clips", "--overwrite"], TRAIN_ENV)
        augmented.touch()
    runner([*base, "--train_model"], TRAIN_ENV)
    model_path = Path(config["output_dir"]) / f"{preset.model_name}.onnx"
    if not model_path.exists():
        raise FileNotFoundError(f"training finished but {model_path} is missing")
    return TrainResult(model_path, added, real.held_out, real.skipped)


# -- checking the finished model ---------------------------------------------------


def score_wavs(model_path: Path, wavs: list[Path], *, pad_s: float = 1.0) -> dict[str, float]:
    """Highest score the model gives each clip (padded with silence, fed in
    80 ms frames like AIForUs does)."""
    from openwakeword.model import Model

    model = Model(wakeword_models=[str(model_path)], inference_framework="onnx")
    key = Path(model_path).stem
    pad = np.zeros(int(SAMPLE_RATE * pad_s), dtype=np.int16)
    scores: dict[str, float] = {}
    for path in wavs:
        audio, rate = read_wav(path)
        pcm = (np.clip(resample(audio, rate), -1, 1) * 32767).astype(np.int16)
        pcm = np.concatenate([pad, pcm, pad])
        model.reset()
        best = 0.0
        for start in range(0, len(pcm) - 1279, 1280):
            best = max(best, float(model.predict(pcm[start : start + 1280])[key]))
        scores[path.name] = best
    return scores
