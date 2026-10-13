# Training the "Hai Nemo" wake word models

AIForUs listens for its name before it sends anything to speech recognition
(see `listening` in [CONFIGURATION.md](../../documentation/CONFIGURATION.md)).
There are two wake word engines:

| Engine | Setup | Hears |
|---|---|---|
| `vosk` (default) | `python -m aiforus --download-models` | "Nemo" / "Hai Nemo" and "help". The small Vosk model is English, so it cannot hear "tolong" or "darurat". |
| `openwakeword` | the two models trained here | "Hai Nemo", "Halo Nemo", "Nemo" **and** "Tolong" / "Darurat" without the name. |

The models are trained once, on Google Colab (openWakeWord training only
runs on Linux), and then run on your own computer.

## Steps

1. **Record your voice (optional, recommended).** On your computer:

   ```bash
   python -m aiforus --record-wake-samples      # 20 recordings per phrase
   python -m aiforus --record-wake-samples 40   # or more
   ```

   Say each phrase after the beep, in your normal voice. More voices
   (family, friends - with their permission), rooms and distances make the
   model better. Recordings are saved in `data/wake_samples/` and never
   leave your computer unless you upload them yourself. Zip that folder into
   `wake_samples.zip` if you want to use it in step 2.

2. **Train on Colab.** Open [`train_nemo.ipynb`](train_nemo.ipynb) in Colab
   (*File → Upload notebook*, or
   `https://colab.research.google.com/github/Khaf-dev/aiforus/blob/master/tools/wakeword/train_nemo.ipynb`
   once this folder is on `master`). Choose *Runtime → Change runtime type →
   T4 GPU*, check the settings cell and *Run all*. With `SIZE = "small"`
   expect about 1.5-3 hours for both models; with `"full"` longer. If Colab
   disconnects, run all again: finished steps are skipped.

3. **Install the models.** Unzip `nemo_wakeword_models.zip` into
   `models/wakeword/`:

   ```
   models/wakeword/hai_nemo.onnx
   models/wakeword/tolong.onnx
   ```

   and set in `config.yaml`:

   ```yaml
   listening:
     wake_engine: "openwakeword"
   ```

   then run `python -m aiforus --download-models` (fetches openWakeWord's
   two small feature models) and `python -m aiforus --check`.

4. **Tune.** The *Check* step of the notebook prints the scores of your
   held-back recordings and of look-alike words. Set
   `listening.wake_threshold` between the two (default 0.5). Raise it if
   Nemo wakes up by itself; lower it if it does not hear you.

## Privacy

- By default (`USE_REAL_RECORDINGS = False`) nothing of yours is uploaded:
  the models learn from synthetic English voices with Indonesian-like
  spellings ("neh moh", "toh long").
- With `USE_REAL_RECORDINGS = True` your recordings are uploaded to
  Google's servers for the training session. Only upload recordings of people
  who agreed, and delete the runtime afterwards (*Runtime → Disconnect and
  delete runtime*).
- To keep everything on your own computer, run the notebook in Jupyter
  inside **WSL2** (Ubuntu) with an NVIDIA GPU instead of Colab. Put
  `wake_samples.zip` next to the notebook; the last cell then saves the zip
  instead of downloading it.

## What is in this folder

| File | What it is |
|---|---|
| `train_nemo.ipynb` | The Colab notebook. **Generated** - do not edit by hand. |
| `nemo_wakeword.py` | The AIForUs part of the recipe: phrases and look-alike words for both models, preparing real recordings (resample to 16 kHz, trim silence, hold 20% back, mix in at ~20% of the positives), running openWakeWord's three steps, scoring the result. Embedded in the notebook. |
| `make_notebook.py` | Builds the notebook from the cells it contains and `nemo_wakeword.py`. Run `python tools/wakeword/make_notebook.py` after changing either; a test fails if the notebook is stale. |

## Why the versions are pinned

The official openWakeWord training notebook no longer runs on current
Colab. The notebook here works around what was found while testing:

| Problem | Fix |
|---|---|
| piper-sample-generator 3.x removed `generate_samples.py`, which `train.py` imports | clone tag `v2.0.0` |
| `piper-phonemize` has no Linux wheel for Python 3.12 | `piper-phonemize-fix` (same module) |
| PyTorch 2.6+ refuses to load the Piper and DeepPhonemizer checkpoints | `TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD=1` for the training steps only; the Piper checkpoint is verified by SHA-256 first |
| torchaudio 2.9+ removed `load`/`info` backends used by the augmentation | `torch==2.8.0`, `torchaudio==2.8.0` + `soundfile` |
| `acoustics` imports `scipy.special.sph_harm`, removed in SciPy 1.17 | `scipy<1.17` |
| `torchmetrics<1` needs `pkg_resources` | `setuptools<81` |
| `train.py` always tries the TFLite export (`default="False"` is truthy) and TensorFlow 2.8 no longer installs | patched to export ONNX only |
| a run cut off during augmentation leaves half-written features that `train.py` then trusts | augmentation is redone unless it finished |

**Tested:** the full chain - install set, clip generation with the pinned
Piper model, mixing in real recordings, augmentation, training, ONNX export,
and loading the result in AIForUs' `OpenWakeWordDetector` - ran end to end
on Linux with Python 3.12 using tiny stand-in data. **Not yet tested:** a
real run on Colab, the dataset downloads from Hugging Face, and the
look-alike phrase generator (its model is downloaded from S3); those were
not reachable from the test machine. Model quality can only be judged after
a real run.
