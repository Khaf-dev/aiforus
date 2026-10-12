# Architecture

AIForUs is a voice-first assistant for blind and low-vision people. The
long-term target is smart glasses; this repository is the software that will
run on the companion device (laptop today, phone or edge board later).

## Request flow

```
 microphone ──► SpeechInput ──► IntentRouter ──► Assistant ──► SpeechQueue ──► TextToSpeech ──► speaker
 (or keyboard)   (hal/stt)      (intents.py)     (assistant.py)  (speech.py)     (hal/tts)
                                                    │
                       ┌────────────────────────────┼──────────────────────────┐
                       ▼                            ▼                          ▼
                 VisionService                FaceService                 Navigator
                 camera + YOLOv8 + EasyOCR    YuNet + SFace + SQLite      Nominatim + OSRM
                 (services/vision.py)         (services/faces.py)         (services/navigation.py)
```

1. `SpeechInput.listen()` returns one utterance (runs in a worker thread).
2. `IntentRouter.parse()` maps it to an `Intent` with slots (name,
   destination, language). Deterministic rules, Indonesian and English.
3. `Assistant.handle()` runs the handler. Handlers call services through
   `asyncio.to_thread` so the event loop never blocks.
4. Replies are queued on the `SpeechQueue` with a priority and spoken by the
   TTS engine.

## Key decisions

| Decision | Why |
| --- | --- |
| **Rule-based intent router, LLM only for unknown questions** | Safety-relevant routing (emergency, exit) must be predictable and testable. The LLM never decides what the assistant *does*. |
| **Emergency is matched first, on the raw utterance** | A missed emergency is far worse than a false one, and a false one only speaks guidance. |
| **Exit requires the whole phrase plus confirmation** | The old substring router shut the app down on "is my friend here" ("friend" contains "end"). |
| **Priority speech queue with interruption** | A future hazard alert must cut off whatever is being read. CRITICAL items also drop stale queued chatter. |
| **Half-duplex listening** | With a real microphone the assistant would otherwise transcribe its own voice. Barge-in needs a wake word or echo cancellation (Fase 1). |
| **Hardware abstraction layer with lazy imports** | Swap laptop webcam → glasses camera by writing one adapter. Tests and CI run without OpenCV, PyAudio, pyttsx3 or ML models. |
| **One TTS thread owns the pyttsx3 engine** | pyttsx3 isn't thread-safe. Interruption uses the engine's `started-word` callback. |
| **"I can't see" is different from "I see nothing"** | Dark or covered frames are reported explicitly; "nothing detected" must never be mistaken for "all clear". |
| **Typed config, secrets only from env** | Typos in `config.yaml` fail at startup; API keys never live in the repo. |
| **Face recognition with YuNet + SFace (OpenCV DNN)** | ~40 MB of ONNX models (~10 MB int8), no C++ build, runs on Raspberry Pi/Jetson/phones — the same code path as the future edge device. Embeddings are L2-normalised so one Euclidean threshold maps to SFace's cosine threshold. dlib stays available as a desktop-only backend; embeddings of different models are stored separately. |
| **Clock directions + rough distance** | Orientation & mobility training uses clock directions. Bearing comes from the box centre and the camera FOV; distance from the pinhole model and a typical height per class, always spoken as "about". Boxes cut off by the frame are "very close" without a number. |
| **Face encodings as raw float64 in SQLite** | `pickle.load` on a replaceable file can execute code. Names are case-insensitive; enrollment refuses frames with several faces. |
| **Every sentence in `locales.py`** | Indonesian first, English kept in sync; a test enforces identical keys and placeholders. |

## Known limitations (tracked in the roadmap)

- Speech recognition uses Google's online API; offline STT is planned.
- Location is IP-based (kilometres off), so navigation is a demo until GPS
  from a phone is available. The public OSRM server only has a car profile.
- No obstacle, traffic or hazard detection yet; sound-based detection from
  v1.1 was removed because it was not reliable (old code: tag `v1.1.0-legacy`).
- Emergency alerts are not sent anywhere yet; the assistant says so.
- The SQLite database (face encodings = biometric data) is not encrypted.
