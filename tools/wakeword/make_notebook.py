"""Build ``train_nemo.ipynb`` from this script and ``nemo_wakeword.py``.

The notebook embeds ``nemo_wakeword.py`` (Colab has no copy of this repo), so
edit the helper or the cells below and run::

    python tools/wakeword/make_notebook.py

``tests/test_wakeword_tools.py`` fails when the committed notebook is stale.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
NOTEBOOK = HERE / "train_nemo.ipynb"
HELPER = HERE / "nemo_wakeword.py"

# Pinned so the recipe does not break when upstream changes (piper-sample-generator
# 3.x already removed what openWakeWord's train.py imports).
OWW_COMMIT = "368c03716d1e92591906a84949bc477f3a834455"
PSG_TAG = "v2.0.0"
PIPER_PT = "en_US-libritts_r-medium.pt"
PIPER_PT_SHA256 = "e95ee53770bf598c354a6e6dbfc95ccb259aeeb501d35a86be8a767429ab0ff6"
FEATURE_MODELS = {
    "melspectrogram.onnx": "ba2b0e0f8b7b875369a2c89cb13360ff53bac436f2895cced9f479fa65eb176f",
    "embedding_model.onnx": "70d164290c1d095d1d4ee149bc5e00543250a7316b59f31d056cff7bd3075c1f",
}

INTRO = """\
# Train the "Hai Nemo" and "Tolong" wake word models

This notebook trains the two [openWakeWord](https://github.com/dscripka/openWakeWord) models AIForUs
uses when `listening.wake_engine` is `openwakeword`:

| File | Listens for | Config key |
|---|---|---|
| `hai_nemo.onnx` | "Hai Nemo", "Halo Nemo", "Nemo" | `listening.openwakeword_wake_model` |
| `tolong.onnx` | "Tolong", "Darurat" (emergency, no name needed) | `listening.openwakeword_emergency_model` |

**Before you start**

1. *Runtime → Change runtime type → T4 GPU*. Without a GPU, generating the clips takes many hours.
2. Choose the settings in the next cell, then *Runtime → Run all*.
3. Expect roughly 1.5-3 hours with `SIZE = "small"` for both models (most of it downloading data and
   generating clips) - longer with `"full"`. If Colab disconnects, run all again: finished steps are skipped.

**Privacy.** By default nothing of yours is uploaded: the models learn from synthetic voices only.
Real recordings of your voice (`python -m aiforus --record-wake-samples`) make the models much better
at Indonesian pronunciation, but using them means uploading them to Google's servers. That is your
choice: set `USE_REAL_RECORDINGS = True` only for recordings of people who agreed, and delete the
runtime afterwards (*Runtime → Disconnect and delete runtime*). To keep recordings on your own
computer instead, run the same steps in WSL2 (see `tools/wakeword/README.md`).
"""

SETTINGS = """\
# "small" = first try (faster), "full" = the size openWakeWord recommends for daily use
SIZE = "small"
# Which models to train: "hai_nemo" (wake word) and/or "tolong" (emergency)
MODELS = ["hai_nemo", "tolong"]
# True = upload wake_samples.zip with your real recordings (see the privacy note above)
USE_REAL_RECORDINGS = False
# Hours of music used as background noise ("small": 1, "full": 3 or more)
MUSIC_HOURS = 1 if SIZE == "small" else 3
"""

INSTALL = f"""\
# Install the training tools (about 5 minutes). Versions are pinned: newer ones break training.
!nvidia-smi -L || echo "No GPU - choose Runtime > Change runtime type > T4 GPU"
!test -d openwakeword || git clone -q https://github.com/dscripka/openWakeWord openwakeword
!git -C openwakeword checkout -q {OWW_COMMIT}
!test -d piper-sample-generator || git clone -q --depth 1 -b {PSG_TAG} https://github.com/rhasspy/piper-sample-generator
!test -f piper-sample-generator/models/{PIPER_PT} || wget -q -O piper-sample-generator/models/{PIPER_PT} https://github.com/rhasspy/piper-sample-generator/releases/download/{PSG_TAG}/{PIPER_PT}
# torchaudio 2.9+ dropped the audio functions openWakeWord's augmentation uses
!pip install -q "torch==2.8.0" "torchaudio==2.8.0" "torchvision==0.23.0" soundfile
!pip install -q -e ./openwakeword piper-phonemize-fix webrtcvad-wheels "mutagen>=1.46,<2" "torchinfo>=1.8,<2" "torchmetrics>=0.11.4,<1" "speechbrain>=0.5.14,<1" "audiomentations>=0.30,<1" "torch-audiomentations>=0.11,<1" "acoustics>=0.2.6,<1" "pronouncing>=0.2,<1" "datasets>=2.14.4,<3" "deep-phonemizer==0.0.19" "scipy<1.17" "setuptools<81" pyyaml onnx onnxruntime

import hashlib, os, subprocess, sys
from pathlib import Path

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()

# The Piper checkpoint is loaded with pickle (see TRAIN_ENV in the helper), so it must be the exact file.
assert sha256(f"piper-sample-generator/models/{PIPER_PT}") == "{PIPER_PT_SHA256}", "unexpected Piper checkpoint - delete it and run again"

resources = Path("openwakeword/openwakeword/resources/models")
resources.mkdir(parents=True, exist_ok=True)
for name, digest in {FEATURE_MODELS!r}.items():
    target = resources / name
    if not target.exists():
        subprocess.run(["wget", "-q", "-O", str(target), f"https://github.com/dscripka/openWakeWord/releases/download/v0.5.1/{{name}}"], check=True)
    assert sha256(target) == digest, f"unexpected {{name}}"
sys.path.insert(0, "openwakeword")  # the editable install is only seen by a restarted kernel
print("Tools ready.")
"""

DATA = """\
# Download background noise, room echoes and the shared negative data (about 20 GB, 20-40 minutes).
import numpy as np, scipy.io.wavfile, datasets
from tqdm.auto import tqdm

def save16k(folder, name, array):
    Path(folder).mkdir(exist_ok=True)
    scipy.io.wavfile.write(os.path.join(folder, name), 16000, (np.clip(array, -1, 1) * 32767).astype(np.int16))

# Room impulse responses (MIT), used to add echo to the clips
# (a ".done" file marks a finished step, so a run cut off half-way starts that step again)
if not Path("mit_rirs/.done").exists():
    for row in tqdm(datasets.load_dataset("davidscripka/MIT_environmental_impulse_responses", split="train", streaming=True), desc="room echoes"):
        save16k("mit_rirs", row["audio"]["path"].split("/")[-1], row["audio"]["array"])
    Path("mit_rirs/.done").touch()

# AudioSet: everyday sounds as background noise
if not Path("audioset_16k/.done").exists():
    !mkdir -p audioset && wget -q -c -O audioset/bal_train09.tar https://huggingface.co/datasets/agkphysics/AudioSet/resolve/main/data/bal_train09.tar && tar -xf audioset/bal_train09.tar -C audioset
    flacs = [str(p) for p in Path("audioset/audio").glob("**/*.flac")]
    audioset = datasets.Dataset.from_dict({"audio": flacs}).cast_column("audio", datasets.Audio(sampling_rate=16000))
    for row in tqdm(audioset, desc="audioset"):
        save16k("audioset_16k", Path(row["audio"]["path"]).with_suffix(".wav").name, row["audio"]["array"])
    Path("audioset_16k/.done").touch()

# Free Music Archive: music as background noise (optional - training still works without it)
background = ["./audioset_16k"]
try:
    if not Path("fma/.done").exists():
        fma = datasets.load_dataset("rudraml/fma", name="small", split="train", streaming=True)
        fma = iter(fma.cast_column("audio", datasets.Audio(sampling_rate=16000)))
        for _ in tqdm(range(MUSIC_HOURS * 3600 // 30), desc="music"):  # 30-second clips
            row = next(fma)
            save16k("fma", Path(row["audio"]["path"]).with_suffix(".wav").name, row["audio"]["array"])
        Path("fma/.done").touch()
    background.append("./fma")
except Exception as error:  # the dataset sometimes moves; music is a nice-to-have
    print("Skipping music background:", error)

# Pre-computed openWakeWord features: ~2,000 hours of speech/noise that must NOT trigger,
# plus the validation set used to estimate false triggers per hour
# (wget -c resumes a download that was cut off, and returns at once when it is complete)
for name in ["openwakeword_features_ACAV100M_2000_hrs_16bit.npy", "validation_set_features.npy"]:
    !wget -q -c https://huggingface.co/datasets/davidscripka/openwakeword_features/resolve/main/{name}
print("Data ready. Background folders:", background)
"""

UPLOAD = """\
# Upload your recordings (only when USE_REAL_RECORDINGS = True).
# On your computer: zip the folder data/wake_samples into wake_samples.zip first.
# Outside Colab, put wake_samples.zip next to this notebook instead.
samples_root = None
if USE_REAL_RECORDINGS:
    if not Path("wake_samples.zip").exists():
        from google.colab import files
        uploaded = files.upload()  # choose wake_samples.zip
        if "wake_samples.zip" not in uploaded:
            raise SystemExit("Please upload a file named wake_samples.zip")
    samples_root = nw.unpack_samples(Path("wake_samples.zip"), Path("wake_samples"))
    for folder in sorted(p for p in samples_root.iterdir() if p.is_dir()):
        print(f"{folder.name}: {len(list(folder.glob('*.wav')))} recordings")
else:
    print("Using synthetic voices only.")
"""

TRAIN = """\
# Train. Each model: generate clips -> add real recordings -> augment -> train (about 30-60 min each on a T4).
import yaml

base_config = yaml.safe_load(open("openwakeword/examples/custom_model.yml"))
results = {}
for name in MODELS:
    print("=" * 30, name, "=" * 30)
    results[name] = nw.train_model(
        nw.PRESETS[name],
        base_config=base_config,
        train_script=Path("openwakeword/openwakeword/train.py"),
        work_dir=Path("."),
        size=SIZE,
        samples_root=samples_root,
        overrides={
            "piper_sample_generator_path": "./piper-sample-generator",
            "output_dir": "./nemo_models",
            "rir_paths": ["./mit_rirs"],
            "background_paths": background,
            "background_paths_duplication_rate": [1] * len(background),
            "false_positive_validation_data_path": "validation_set_features.npy",
            "feature_data_files": {"ACAV100M_sample": "openwakeword_features_ACAV100M_2000_hrs_16bit.npy"},
        },
    )
    print("Saved", results[name].model_path)
"""

CHECK = """\
# Check the models on clips they did not learn from.
import random

for name, result in results.items():
    print("=" * 30, name, "=" * 30)
    negatives = sorted(Path("nemo_models", name, "negative_test").glob("*.wav"))
    negatives = random.Random(0).sample(negatives, min(100, len(negatives)))
    neg = nw.score_wavs(result.model_path, negatives)
    print(f"Look-alike words (should stay LOW): {sum(s >= 0.5 for s in neg.values())}/{len(neg)} reach 0.5")
    if result.held_out:
        real = nw.score_wavs(result.model_path, result.held_out)
        for clip, score in sorted(real.items()):
            print(f"  {score:.2f}  {clip}")
        print(f"Your held-back recordings (should be HIGH): {sum(s >= 0.5 for s in real.values())}/{len(real)} reach 0.5")
print("Pick listening.wake_threshold between the two groups; 0.5 is the default.")
"""

DOWNLOAD = """\
# Download the models, then on your computer:
#   1. unzip into models/wakeword/  (models/wakeword/hai_nemo.onnx, models/wakeword/tolong.onnx)
#   2. config.yaml -> listening.wake_engine: "openwakeword"
#   3. python -m aiforus --check
import zipfile
with zipfile.ZipFile("nemo_wakeword_models.zip", "w") as z:
    for result in results.values():
        z.write(result.model_path, result.model_path.name)
try:
    from google.colab import files
    files.download("nemo_wakeword_models.zip")
except ImportError:  # running outside Colab (e.g. Jupyter in WSL2)
    print("Models zipped to", Path("nemo_wakeword_models.zip").resolve())
"""


def _lines(text: str) -> list[str]:
    lines = text.splitlines(keepends=True)
    if lines:
        lines[-1] = lines[-1].rstrip("\n")
    return lines


def _markdown(text: str) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _lines(text)}


def _code(text: str) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _lines(text),
    }


def build() -> str:
    helper = HELPER.read_text(encoding="utf-8")
    cells = [
        _markdown(INTRO),
        _code(SETTINGS),
        _markdown("## 1. Install"),
        _code(INSTALL),
        _markdown(
            "## 2. Helper\nThe AIForUs helper (`tools/wakeword/nemo_wakeword.py`): phrases, real recordings, checks."
        ),
        _code("%%writefile nemo_wakeword.py\n" + helper),
        _code("import importlib, nemo_wakeword as nw\nimportlib.reload(nw);"),
        _markdown("## 3. Training data"),
        _code(DATA),
        _markdown("## 4. Your recordings (optional)"),
        _code(UPLOAD),
        _markdown("## 5. Train"),
        _code(TRAIN),
        _markdown("## 6. Check"),
        _code(CHECK),
        _markdown("## 7. Download"),
        _code(DOWNLOAD),
    ]
    notebook = {
        "cells": cells,
        "metadata": {
            "accelerator": "GPU",
            "colab": {"provenance": [], "gpuType": "T4"},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "nbformat": 4,
        "nbformat_minor": 0,
    }
    return json.dumps(notebook, indent=1, ensure_ascii=False) + "\n"


def main() -> int:
    NOTEBOOK.write_text(build(), encoding="utf-8")
    print(f"wrote {NOTEBOOK}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
