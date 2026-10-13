# Agent guide — AIForUs

Voice-first vision assistant for blind and low-vision people. Research
prototype; the long-term target is smart glasses (glasses = camera, mic,
speaker; compute on a phone/laptop/edge board). Bahasa Indonesia first,
English kept in sync.

Read first: `README.md`, `documentation/ARCHITECTURE.md`.

## Layout

- `aiforus/cli.py` — entry point, `--check`, builds optional components and records why one is unavailable.
- `aiforus/config.py` — typed settings (pydantic, `extra="forbid"`) from `config.yaml`; secrets from env only.
- `aiforus/intents.py` — deterministic rule-based router (id + en). Emergency first; rule order matters.
- `aiforus/assistant.py` — one handler per intent; all dependencies injected.
- `aiforus/speech.py` — priority speech queue with interruption.
- `aiforus/locales.py`, `aiforus/i18n.py` — every spoken sentence, in `id` and `en`.
- `aiforus/storage.py` — SQLite via SQLAlchemy 2.0 (no pickle).
- `aiforus/hal/` — camera, microphone, TTS (Piper, pyttsx3), location, console adapters (lazy imports).
- `aiforus/services/` — vision (YOLOv8, EasyOCR), spatial (clock direction + distance),
  faces (YuNet + SFace / dlib), imaging (JPEG for the VLM), llm (OpenAI-compatible
  `answer()` / `look()`), navigation.
- `tests/` — pytest, hardware faked in `tests/fakes.py`.

## Rules

- Every spoken string goes in `locales.py` for **both** languages (a test enforces identical keys and placeholders).
- Never make the assistant claim something is safe ("path clear", "no obstacles", "safe to cross").
  Report what was detected and what can't be detected. Distances are always "about".
- "I can't see" (dark, covered, no camera) must never be reported as "nothing there".
- The LLM/VLM never decides which command runs. Obstacle questions never go to the VLM.
- Camera images never leave the machine unless `llm.allow_images_to_cloud` is true, and every cloud send is announced.
- Secrets only from env / `.env`; never from `config.yaml`, never logged.
- Heavy libraries (cv2, torch, ultralytics, easyocr, face_recognition, piper, pyttsx3,
  speech_recognition, openai) are imported lazily inside adapters only.
- Blocking work runs via `asyncio.to_thread`; HTTP and model calls always have a timeout.
- New user-facing behaviour: update `documentation/VOICE_COMMANDS.md`, new settings:
  `config.yaml` + `documentation/CONFIGURATION.md`, and `CHANGELOG.md` (Unreleased).

## Validate

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
python -m aiforus --check
printf "bantuan\nmatikan asisten\nya\n" | python -m aiforus --text --mute
```