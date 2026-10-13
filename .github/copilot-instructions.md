# Agent guide — AIForUs

Voice-first vision assistant for blind and low-vision people. Research
prototype; the long-term target is smart glasses (glasses = camera, mic,
speaker; compute on a phone/laptop).

## Layout

- `aiforus/config.py` — typed settings (pydantic) from `config.yaml`; secrets from env.
- `aiforus/intents.py` — deterministic rule-based router (id + en). Emergency first.
- `aiforus/assistant.py` — orchestrator; all dependencies injected.
- `aiforus/speech.py` — priority speech queue with interruption.
- `aiforus/hal/` — camera, microphone, TTS, location adapters (lazy imports).
- `aiforus/services/` — vision (YOLOv8, EasyOCR), faces, navigation, LLM.
- `aiforus/storage.py` — SQLite via SQLAlchemy 2.0 (no pickle).
- `aiforus/locales.py` — every spoken sentence, in `id` and `en`.
- `tests/` — pytest, hardware faked in `tests/fakes.py`.

## Rules

- Every spoken string goes in `locales.py` for **both** languages.
- Never make the assistant claim something is safe ("path clear", "safe to cross").
  Report what was detected and what can't be detected.
- Heavy libraries (cv2, torch, ultralytics, easyocr, face_recognition, pyttsx3,
  speech_recognition, openai) are imported lazily inside adapters only.
- Blocking work runs via `asyncio.to_thread`; HTTP calls always have a timeout.

## Validate

```bash
pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest -q
python -m aiforus --check
printf "bantuan\nmatikan asisten\nya\n" | python -m aiforus --text --mute
```
