# AIForUs — Vision Assistant for Blind and Low-Vision People

[![CI](https://github.com/Khaf-dev/aiforus/actions/workflows/ci.yml/badge.svg)](https://github.com/Khaf-dev/aiforus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Status: research prototype](https://img.shields.io/badge/status-research%20prototype-orange.svg)

AIForUs is a voice-first assistant that describes the surroundings, reads
text and documents, recognises people the user has enrolled, answers
questions about what the camera sees and gives walking directions — all by
voice, with no screen. Bahasa Indonesia first, English supported.

The long-term goal is a pair of smart glasses: the glasses provide the
camera, microphone and speaker; the processing runs on a companion device
(phone, laptop or edge board). Today it runs on a laptop with a webcam and
headphones.

> **Safety notice.** This is a research prototype, not a mobility aid. It
> does **not** detect obstacles, traffic or hazards yet, and it never tells
> you that something is safe. Keep using your white cane or guide dog.

**Contents:** [What works](#what-works-today) ·
[Example](#what-it-sounds-like) · [Quick start](#quick-start-windows) ·
[Usage](#usage) · [Privacy](#privacy) · [How it works](#how-it-works) ·
[Configuration](#configuration) · [Troubleshooting](#troubleshooting) ·
[Development](#development) · [Roadmap](#roadmap)

## What works today

| Capability | Status | How |
| --- | --- | --- |
| Voice commands (id / en) | ✅ | Deterministic rule-based router; Google speech recognition (online) |
| Spoken replies | ✅ | Offline neural TTS ([Piper](https://github.com/OHF-Voice/piper1-gpl)) with a natural Indonesian voice, pyttsx3 fallback; prioritised and interruptible |
| Describe surroundings (fast) | ✅ | YOLOv8n on this machine, with clock directions and rough distance: *"Kursi di jam 1, sekitar 2 meter."* |
| Detailed description, documents, questions about the image | ✅ optional | Vision-language model, local by default (Ollama `gemma3:4b`): *"jelaskan lebih detail"*, *"baca dokumen"*, *"lihat, ini uang berapa?"* |
| Read short text | ✅ | EasyOCR (Indonesian + English), reading order |
| Recognise people | ✅ | Enroll by voice (3 samples per command); YuNet + SFace — small ONNX models that also run on edge devices; stored locally |
| General questions | ✅ optional | Any OpenAI-compatible LLM: local and free with Ollama, or a hosted provider |
| Walking directions | ⚠️ demo | Nominatim + OSRM, turn-by-turn; start point from IP (kilometres off) |
| Emergency | ⚠️ partial | Immediate spoken guidance + approximate location; does **not** send alerts yet |
| Obstacles, traffic, hazards, sound events | ❌ planned | See [roadmap](#roadmap) — the assistant says so honestly when asked |

## What it sounds like

```
You:  "apa di depan"
AIForUs: "Orang di jam 11, sekitar 1,5 meter. Kursi di jam 1, sekitar 2 meter."

You:  "siapa ini"
AIForUs: "Aku melihat 1 wajah. Yang aku kenal: Budi."

You:  "lihat, ini uang berapa?"
AIForUs: "Sebentar, aku perhatikan dulu."  …  (the vision model's answer, a few seconds later)

You:  "ada rintangan?"
AIForUs: "… deteksi rintangan lewat suara belum tersedia … Tetap gunakan tongkat."
         (it never says "the path is clear")
```

Clock directions are the convention taught in orientation & mobility
training: 12 = straight ahead, 3 = right, 9 = left. Distances are estimates
and are always said with *sekitar* / *about*.

## Quick start (Windows)

Requires Python 3.10–3.13, a webcam, a microphone and speakers/headphones.
Plan for a few GB of disk: PyTorch, YOLO/EasyOCR and the voice models.

**1. Install**

```powershell
git clone https://github.com/Khaf-dev/aiforus.git
cd aiforus
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip

# Voice, natural voice, camera features and the LLM client
pip install -e ".[voice,piper,vision,llm]"

# Piper voices (id + en, ~60 MB each) and face models (~40 MB)
python -m aiforus --download-models
```

**2. Optional — local AI for general questions and detailed vision**

Install [Ollama](https://ollama.com), then:

```powershell
ollama pull gemma3:4b
```

The default `config.yaml` already points at it. Without Ollama everything
else still works; those two features just say they aren't available.

**3. Check what works on your machine**

```powershell
python -m aiforus --check
```

```
  voice output (piper)       ok
  voice input                ok
  camera                     ok
  object detection           ok
  text reading               ok
  face recognition (opencv)  ok
  navigation                 ok
  location                   ok
  general questions (LLM)    ok - gemma3:4b @ http://localhost:11434/v1
  detailed vision (VLM)      ok - gemma3:4b (local, images stay on this machine)
  TTS voice for 'id' (piper) found
  TTS voice for 'en' (piper) found
  camera frame               ok (720, 1280, 3)
  LLM server                 reachable, model found
```

Anything that isn't `ok` says why; see
[Troubleshooting](documentation/TROUBLESHOOTING.md).

**4. Run it**

```powershell
python -m aiforus
```

Say **"bantuan"** to hear what it can do.

> **Linux / macOS:** the same steps work (`source .venv/bin/activate`).
> PyAudio needs the PortAudio headers first: `sudo apt install portaudio19-dev`
> on Debian/Ubuntu, `brew install portaudio` on macOS.

## Usage

```powershell
python -m aiforus                  # talk to it
python -m aiforus --text           # type commands, hear replies
python -m aiforus --text --mute    # type commands, read replies (no audio)
python -m aiforus --lang en        # English
python -m aiforus --check          # component report, then exit
python -m aiforus --debug          # verbose logs
```

`python app.py` still works and does the same as `python -m aiforus`.

Commands at a glance (full list with English:
[documentation/VOICE_COMMANDS.md](documentation/VOICE_COMMANDS.md)):

| Want to… | Say |
| --- | --- |
| Get help **now** | "tolong", "darurat", "saya jatuh" |
| Hear the command list | "bantuan" |
| Know what's in front (fast) | "apa di depan" |
| Get a detailed description | "jelaskan lebih detail" |
| Read a letter, menu or label | "baca dokumen", "bacakan menu" |
| Ask about what the camera sees | "lihat, baju ini warna apa?" |
| Read short text | "baca tulisan" |
| Know who's there | "siapa ini" |
| Save someone's face | "kenali wajah sebagai Budi" |
| Stop talking | "diam" |
| Turn it off | "matikan asisten", then "ya" |

Anything else is treated as a general question for the LLM.

## Privacy

| Data | Where it goes |
| --- | --- |
| Your voice | Sent to Google's speech recognition service (needs internet). Offline recognition is planned. |
| Camera images | Processed on this machine and never stored. Detailed descriptions send one photo to the configured vision model — **local by default**. A cloud model is used only if you set `llm.allow_images_to_cloud: true`, and the assistant then says so every time. |
| Face encodings | Stored locally in `data/aiforus.db`. Not encrypted yet — keep that folder private. Ask people before enrolling their face. |
| General questions | Stay on your machine with a local LLM (Ollama); sent to the provider only if you configure a hosted one. |
| Location | Your IP is sent to ipinfo.io; destination searches go to OpenStreetMap Nominatim and OSRM. |
| Conversations | Not stored. What you said is printed to the console log only (not written to any file). |

## How it works

```
mic/keyboard ─► SpeechInput ─► IntentRouter ─► Assistant ─► SpeechQueue ─► TTS ─► speaker
                                                  │
         ┌───────────────┬───────────────┬────────┴───────┬──────────────────┐
         ▼               ▼               ▼                ▼                  ▼
   VisionService     FaceService    Vision-language    LLM answers       Navigator
   YOLOv8 + OCR      YuNet + SFace  model (VLM)        (general Q&A)     Nominatim + OSRM
   + clock/distance  + SQLite       "jelaskan/lihat"
   fast, local       local          local by default   local by default  online
```

- Commands are matched by **deterministic rules**, never by the LLM — an
  emergency or "turn off" must be predictable and testable.
- There are **two speeds of seeing**: "apa di depan" is fast local object
  detection; "jelaskan lebih detail" / "lihat, …" use a slower but richer
  vision-language model.
- Hardware sits behind small interfaces in `aiforus/hal/`, so moving from a
  laptop webcam to smart glasses means writing one adapter.

Design decisions, data flows and known limitations:
[documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md).

## Configuration

Non-secret settings live in [`config.yaml`](config.yaml) — camera, voice
speed, thresholds, models. Unknown keys are rejected at startup, so typos
fail loudly. Secrets (`LLM_API_KEY`) come only from the environment or a
`.env` file (see [`.env.example`](.env.example)).

Every setting is described in
[documentation/CONFIGURATION.md](documentation/CONFIGURATION.md), including
recipes for:

- **Local LLM / VLM with Ollama** (default) or a **hosted provider**
  (OpenAI or any OpenAI-compatible API).
- **Calibrating distances** to your camera.
- **Edge devices** (int8 face models).

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `TTS voice for 'id' … NOT FOUND` | `pip install -e ".[piper]"` and `python -m aiforus --download-models` |
| Windows: nothing happens until you press Enter | Fixed in the current version (console QuickEdit is disabled while running). Update. |
| `LLM server NOT reachable` | Start Ollama (`ollama serve` or the tray app) and `ollama pull gemma3:4b` |
| `detailed vision (VLM) blocked` | The endpoint is in the cloud; set `llm.allow_images_to_cloud: true` only if you accept sending photos |
| Distances are consistently off | [Calibrate](documentation/CONFIGURATION.md#calibrating-distances) `vision.face_height_m` / `camera.horizontal_fov_deg` |

More: [documentation/TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md).

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
```

The test-suite fakes the camera, microphone, TTS engine and ML models, so it
runs anywhere in a few seconds without a GPU; CI runs it on Python 3.10–3.13.

```
aiforus/
├── cli.py            entry point, --check, wiring of optional components
├── config.py         typed settings (pydantic); secrets from env only
├── intents.py        rule-based intent router (id + en), emergency first
├── assistant.py      command handlers
├── speech.py         priority speech queue with interruption
├── locales.py        every spoken sentence, in id and en
├── storage.py        SQLite (face embeddings, preferences)
├── downloads.py      Piper voices and face models
├── hal/              camera, microphone, TTS (Piper, pyttsx3), location, console
└── services/         vision, spatial (clock + distance), faces, imaging, llm, navigation
tests/                pytest, hardware faked in tests/fakes.py
documentation/        architecture, configuration, voice commands, troubleshooting
```

Contribution rules (every sentence in both languages, never claim something
is safe, heavy imports stay lazy) are in
[.github/copilot-instructions.md](.github/copilot-instructions.md).

## Roadmap

- **Fase 0 — Foundation** ✅ safety fixes, new architecture, tests, honest docs.
- **Fase 1 — Real-time perception**
  - ✅ object positions with clock directions and distance
  - ✅ natural Indonesian voice (Piper)
  - ✅ edge-ready face recognition, multi-sample enrollment
  - ✅ any OpenAI-compatible LLM, local by default
  - ✅ detailed descriptions, documents and image questions (VLM)
  - next: offline Indonesian speech recognition, push-to-talk / wake word
    with barge-in
- **Fase 2 — Hazards:** depth estimation for head-level obstacles, vehicle
  tracking, pedestrian lights, sound events (horns, sirens), real emergency alerts.
- **Fase 3 — Hardware:** smart-glasses adapter, phone GPS, heading.
- **Fase 4 — User testing** with blind and low-vision users.

Release notes: [CHANGELOG.md](CHANGELOG.md).

## Documentation

| Document | What's in it |
| --- | --- |
| [VOICE_COMMANDS.md](documentation/VOICE_COMMANDS.md) | Every command in Indonesian and English, how answers are phrased |
| [CONFIGURATION.md](documentation/CONFIGURATION.md) | Every `config.yaml` key, LLM/VLM providers, distance calibration |
| [ARCHITECTURE.md](documentation/ARCHITECTURE.md) | Request flow, modules, design decisions, data flows, limitations |
| [TROUBLESHOOTING.md](documentation/TROUBLESHOOTING.md) | Common problems and fixes |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each release |

## License

MIT — see [LICENSE](LICENSE).

Optional dependencies keep their own licenses. Notably `piper-tts` (the
`piper` extra) is GPL-3.0-or-later, each Piper voice model has its own
license on its model card, and Ollama models (e.g. Gemma) come with their
own terms of use. Distributing a bundle that includes them must respect
those terms.

Contact: rifyatkaffa@gmail.com · [GitHub issues](https://github.com/Khaf-dev/aiforus/issues)
