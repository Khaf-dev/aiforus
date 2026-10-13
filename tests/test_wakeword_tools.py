"""The wake word training kit in tools/wakeword (runs on Colab, tested here)."""

import importlib.util
import io
import json
import sys
import wave
import zipfile
from pathlib import Path

import numpy as np
import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools" / "wakeword"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, TOOLS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclasses need the module registered
    spec.loader.exec_module(module)
    return module


nw = _load("nemo_wakeword")
make_notebook = _load("make_notebook")
RATE = 16000


def _wav_bytes(audio, rate=RATE, channels=1):
    pcm = (np.clip(audio, -1, 1) * 32767).astype("<i2")
    if channels == 2:
        pcm = np.repeat(pcm, 2)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())
    return buf.getvalue()


def _recording(rate=RATE, speech_s=0.6, lead_s=0.4, tail_s=1.0, seed=0):
    rng = np.random.default_rng(seed)
    t = np.arange(int(rate * speech_s)) / rate
    speech = 0.4 * np.sin(2 * np.pi * 220 * t)
    hiss = lambda s: rng.normal(0, 0.002, int(rate * s))  # noqa: E731
    return np.concatenate([hiss(lead_s), speech, hiss(tail_s)])


def test_notebook_is_up_to_date():
    # The notebook embeds nemo_wakeword.py; run tools/wakeword/make_notebook.py after editing either.
    assert (TOOLS / "train_nemo.ipynb").read_text(encoding="utf-8") == make_notebook.build()


def test_notebook_embeds_the_helper_and_is_valid_json():
    notebook = json.loads(make_notebook.build())
    sources = ["".join(cell["source"]) for cell in notebook["cells"]]
    helper = (TOOLS / "nemo_wakeword.py").read_text(encoding="utf-8")
    assert "%%writefile nemo_wakeword.py\n" + helper.rstrip("\n") in sources
    # Nothing of the user's is uploaded unless they choose to.
    assert any("USE_REAL_RECORDINGS = False" in s for s in sources)


def test_presets_match_the_recorder_and_the_config_defaults():
    from aiforus.config import ListeningSettings
    from aiforus.wake_samples import PHRASES

    folders = {f for preset in nw.PRESETS.values() for f in preset.sample_folders}
    assert folders == set(PHRASES)
    defaults = ListeningSettings()
    assert f"{nw.PRESETS['hai_nemo'].model_name}.onnx" == defaults.openwakeword_wake_model
    assert f"{nw.PRESETS['tolong'].model_name}.onnx" == defaults.openwakeword_emergency_model
    for preset in nw.PRESETS.values():
        assert not set(preset.target_phrase) & set(preset.negative_phrases)


def test_make_config_keeps_base_and_applies_overrides():
    base = {"model_name": "my_model", "layer_size": 32, "steps": 50000, "output_dir": "./x"}
    config = nw.make_config(base, nw.PRESETS["tolong"], size="small", output_dir="./out")
    assert config["model_name"] == "tolong"
    assert "tolong" in config["target_phrase"] and "tulang" in config["custom_negative_phrases"]
    assert (config["n_samples"], config["steps"]) == nw.SIZES["small"][::2]
    assert config["layer_size"] == 32 and config["output_dir"] == "./out"
    assert base["model_name"] == "my_model"  # the base is not modified


def test_trim_silence_keeps_the_phrase_with_a_small_margin():
    audio = _recording()
    trimmed = nw.trim_silence(audio)
    assert 0.6 <= len(trimmed) / RATE <= 0.85
    assert np.abs(trimmed).max() == pytest.approx(np.abs(audio).max())


def test_trim_silence_rejects_a_silent_recording():
    rng = np.random.default_rng(1)
    assert len(nw.trim_silence(rng.normal(0, 0.002, RATE * 2))) == 0


def test_resample_to_16k():
    pytest.importorskip("scipy")
    audio = _recording(rate=22050)
    out = nw.resample(audio, 22050)
    assert abs(len(out) - len(audio) * RATE / 22050) <= 1


def test_prepare_and_add_real_clips(tmp_path):
    samples = tmp_path / "wake_samples"
    for folder in ("hai_nemo", "halo_nemo", "nemo"):
        for i in range(4):
            path = samples / folder / f"{folder}_{i + 1:03d}.wav"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(_wav_bytes(_recording(seed=i), channels=2 if i == 0 else 1))
    (samples / "nemo" / "nemo_099.wav").write_bytes(_wav_bytes(np.zeros(RATE * 2)))  # failed recording

    real = nw.prepare_real_clips(samples, nw.PRESETS["hai_nemo"], tmp_path / "real")
    assert len(real.train) + len(real.held_out) == 12
    assert len(real.held_out) == round(12 * 0.2)
    assert [p.name for p in real.skipped] == ["nemo_099.wav"]
    audio, rate = nw.read_wav(real.train[0])
    assert rate == RATE and len(audio) < RATE * 1.0  # trimmed

    positive = tmp_path / "positive_train"
    added = nw.add_to_training(real.train, positive, n_synthetic=300, share=0.2)
    # 300 synthetic + added real ~ 20% real
    assert added == len(list(positive.glob("real_*.wav")))
    assert 0.15 <= added / (300 + added) <= 0.3


def test_add_to_training_without_clips_adds_nothing(tmp_path):
    assert nw.add_to_training([], tmp_path, n_synthetic=100) == 0


def test_unpack_samples_finds_the_phrase_folders(tmp_path):
    archive = tmp_path / "wake_samples.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("wake_samples/tolong/tolong_001.wav", _wav_bytes(_recording()))
    root = nw.unpack_samples(archive, tmp_path / "out")
    assert (root / "tolong" / "tolong_001.wav").exists()


def test_unpack_samples_rejects_unsafe_paths(tmp_path):
    archive = tmp_path / "evil.zip"
    with zipfile.ZipFile(archive, "w") as z:
        z.writestr("../escape.wav", b"x")
    with pytest.raises(ValueError, match="unsafe"):
        nw.unpack_samples(archive, tmp_path / "out")
    assert not (tmp_path / "escape.wav").exists()


def test_train_model_runs_the_steps_in_order_with_real_clips_between(tmp_path):
    pytest.importorskip("yaml")
    samples = tmp_path / "wake_samples"
    for i in range(5):
        path = samples / "tolong" / f"tolong_{i + 1:03d}.wav"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(_wav_bytes(_recording(seed=i)))
    out = tmp_path / "models"
    calls = []

    def fake_runner(cmd, env):
        step = cmd[-1] if cmd[-1] != "--overwrite" else cmd[-2]
        calls.append((step, env))
        positive = out / "tolong" / "positive_train"
        if step == "--generate_clips":
            positive.mkdir(parents=True, exist_ok=True)
            for i in range(40):
                (positive / f"syn{i}.wav").write_bytes(b"")
        if step == "--augment_clips":
            calls.append(("real at augment", len(list(positive.glob("real_*.wav")))))
        if step == "--train_model":
            (out / "tolong.onnx").write_bytes(b"onnx")

    train_script = tmp_path / "train.py"
    train_script.write_text("    if args.convert_to_tflite:\n        convert()\n")
    kwargs = dict(
        base_config={"layer_size": 32},
        train_script=train_script,
        work_dir=tmp_path,
        samples_root=samples,
        overrides={"output_dir": str(out)},
        runner=fake_runner,
    )
    result = nw.train_model(nw.PRESETS["tolong"], **kwargs)
    steps = [c[0] for c in calls]
    assert steps == ["--generate_clips", "--augment_clips", "real at augment", "--train_model"]
    assert calls[2][1] == result.real_added > 0
    assert all(env == nw.TRAIN_ENV for step, env in calls if step.startswith("--"))
    assert result.model_path == out / "tolong.onnx" and len(result.held_out) == 1
    assert "if args.convert_to_tflite is True:" in train_script.read_text()  # ONNX only

    # Running again (after a disconnect) adds no second set of copies and skips finished augmentation.
    calls.clear()
    again = nw.train_model(nw.PRESETS["tolong"], **kwargs)
    assert [c[0] for c in calls] == ["--generate_clips", "--train_model"]
    assert again.real_added == result.real_added


def test_patch_train_script_refuses_an_unknown_version(tmp_path):
    script = tmp_path / "train.py"
    script.write_text("print('something else')\n")
    with pytest.raises(RuntimeError, match="changed upstream"):
        nw.patch_train_script(script)
