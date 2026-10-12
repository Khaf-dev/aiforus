# AIForUs — Vision Assistant for Blind and Low-Vision People

[![CI](https://github.com/Khaf-dev/aiforus/actions/workflows/ci.yml/badge.svg)](https://github.com/Khaf-dev/aiforus/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![Status: research prototype](https://img.shields.io/badge/status-research%20prototype-orange.svg)

AIForUs is a voice-first assistant that describes the surroundings, reads
text, recognises people the user has enrolled and gives walking directions —
all by voice, with no screen. Bahasa Indonesia first, English supported.

The long-term goal is a pair of smart glasses: the glasses provide the
camera, microphone and speaker; the processing runs on a companion device.
Today it runs on a laptop with a webcam and headphones.

> **Safety notice.** This is a research prototype, not a mobility aid. It
> does **not** detect obstacles, traffic or hazards yet, and it never tells
> you that something is safe. Keep using your white cane or guide dog.

## What works today

| Capability | Status | How |
| --- | --- | --- |
| Voice commands (id / en) | ✅ | Rule-based router, Google speech recognition (online) |
| Spoken replies | ✅ | Offline neural TTS (Piper) with a natural Indonesian voice, pyttsx3 fallback; prioritised and interruptible |
| Describe surroundings | ✅ | YOLOv8n object detection with clock directions and rough distance ("chair at 1 o'clock, about 2 meters") |
| Read text | ✅ | EasyOCR (Indonesian + English), reading order |
| Recognise people | ✅ | Enroll by voice; YuNet + SFace (small ONNX models that also run on edge devices), stored locally |
| Walking directions | ⚠️ demo | Nominatim + OSRM, turn-by-turn; start point from IP (km off) |
| General questions | ✅ optional | LLM, only if `OPENAI_API_KEY` is set |
| Emergency | ⚠️ partial | Immediate spoken guidance + location; does **not** send alerts yet |
| Obstacles, traffic, hazards, sound events | ❌ planned | See roadmap |

## Quick start (Windows)

Requires Python 3.10–3.13, a webcam, a microphone and speakers/headphones.

```powershell
git clone https://github.com/Khaf-dev/aiforus.git
cd aiforus
python -m venv .venv
.venv\Scripts\activate
python -m pip install -U pip

# Voice + camera features (downloads PyTorch, a few hundred MB)
pip install -e ".[voice,piper,vision]"
# Natural offline voices for Indonesian and English (~60 MB each)
# Piper voices (id + en, ~60 MB each) and face models (~40 MB)
python -m aiforus --download-models
# Optional: answers to general questions
pip install -e ".[llm]"
copy .env.example .env   # then put your OPENAI_API_KEY in .env
```

Check what works on your machine:

```powershell
python -m aiforus --check
```

It lists every component and whether a voice is available for each
language. Speech uses [Piper](https://github.com/OHF-Voice/piper1-gpl)
(offline, neural) when it is installed and its voices are downloaded, and
falls back to the operating system's voices (pyttsx3) otherwise — set
`speech.engine` in `config.yaml` to force one. Windows rarely ships an
Indonesian voice that pyttsx3 can see, which is why Piper is recommended.

Run it:

```powershell
python -m aiforus              # talk to it
python -m aiforus --text       # type commands, hear replies
python -m aiforus --text --mute  # type commands, read replies (no audio)
python -m aiforus --lang en    # English
```

`python app.py` still works and does the same as `python -m aiforus`.

Say **"bantuan"** to hear the commands. Full list:
[documentation/VOICE_COMMANDS.md](documentation/VOICE_COMMANDS.md).

## Privacy

| Data | Where it goes |
| --- | --- |
| Your voice | Sent to Google's speech recognition service (needs internet). Offline recognition is planned. |
| Camera images | Processed locally; never stored or uploaded. |
| Face encodings | Stored locally in `data/aiforus.db`. Not encrypted yet — keep that folder private. Ask people before enrolling their face. |
| General questions | Sent to OpenAI only if you set `OPENAI_API_KEY`. |
| Location | Your IP is sent to ipinfo.io; destination searches go to OpenStreetMap Nominatim and OSRM. |

## Architecture

```
mic/keyboard → SpeechInput → IntentRouter → Assistant → SpeechQueue → TTS → speaker
                                              ├─ VisionService (camera, YOLOv8, EasyOCR)
                                              ├─ FaceService (YuNet + SFace, SQLite)
                                              └─ Navigator (Nominatim, OSRM)
```

Hardware sits behind small interfaces in `aiforus/hal/`, so moving from a
laptop webcam to smart glasses means writing one adapter. Design decisions
and known limitations: [documentation/ARCHITECTURE.md](documentation/ARCHITECTURE.md).

## Configuration

Non-secret settings live in [`config.yaml`](config.yaml) (camera index, TTS
speed, confidence thresholds, ...). Unknown keys are rejected at startup.
Secrets (`OPENAI_API_KEY`) come from the environment or `.env`.

## Development

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
```

The test-suite fakes the camera, microphone, TTS engine and ML models, so it
runs anywhere in a few seconds; CI runs it on Python 3.10–3.13.

## Roadmap

- **Fase 0 — Foundation** ✅ safety fixes, new architecture, tests, honest docs.
- **Fase 1 — Real-time perception:** ✅ object positions ("chair at 2 o'clock,
  about 2 meters"), ✅ natural Indonesian voice (Piper), ✅ edge-ready face
  recognition; next: rich scene descriptions, offline Indonesian speech
  recognition, push-to-talk / wake word.
- **Fase 2 — Hazards:** depth estimation for head-level obstacles, vehicle
  tracking, pedestrian lights, sound events (horns, sirens), real emergency alerts.
- **Fase 3 — Hardware:** smart-glasses adapter, phone GPS, heading.
- **Fase 4 — User testing** with blind and low-vision users.

## License

MIT — see [LICENSE](LICENSE).

Optional dependencies keep their own licenses. Notably `piper-tts` (the
`piper` extra) is GPL-3.0-or-later, and each Piper voice model has its own
license on its model card. Distributing a bundle that includes them must
respect those terms.

Contact: rifyatkaffa@gmail.com · [GitHub issues](https://github.com/Khaf-dev/aiforus/issues)
