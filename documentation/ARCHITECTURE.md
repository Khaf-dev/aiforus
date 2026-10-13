# Architecture

AIForUs is a voice-first assistant for blind and low-vision people. The
long-term target is smart glasses; this repository is the software that will
run on the companion device (a laptop today, a phone or edge board later).
The glasses themselves only need a camera, a microphone and a speaker.

## Request flow

```
 microphone ──► SpeechInput ──► IntentRouter ──► Assistant ──► SpeechQueue ──► TextToSpeech ──► speaker
 (or keyboard)   hal/stt.py     intents.py       assistant.py   speech.py      hal/piper_tts.py
                                                     │                          hal/tts.py (pyttsx3)
     ┌──────────────────┬──────────────────┬─────────┴─────────┬───────────────────┐
     ▼                  ▼                  ▼                   ▼                   ▼
 VisionService      FaceService       VisionAnswerer      Answerer            Navigator
 camera, YOLOv8,    YuNet + SFace,    one JPEG → VLM      text → LLM          Nominatim + OSRM
 EasyOCR            SQLite            services/llm.py     services/llm.py     services/navigation.py
 services/vision.py services/faces.py + imaging.py
   + spatial.py
```

1. `SpeechInput.listen()` returns one utterance (in a worker thread). While
   the assistant is speaking it doesn't listen (half-duplex), so it never
   transcribes its own voice.
2. `IntentRouter.parse()` normalises the text (lowercase, no punctuation,
   polite words stripped) and maps it to an `Intent` with slots (name,
   destination, language, question). Deterministic rules, Indonesian and
   English, **emergency first**.
3. `Assistant.handle()` runs the handler. Blocking work (camera, models,
   HTTP) runs through `asyncio.to_thread`, so the event loop never blocks.
4. Replies go on the `SpeechQueue` with a priority and are spoken by the TTS
   engine; anything can be interrupted.

## Modules

| Module | Responsibility |
| --- | --- |
| `cli.py` | Entry point. Builds every optional component, records why one is unavailable (shown by `--check`), wires them into the `Assistant`. |
| `config.py` | Typed settings (pydantic, unknown keys rejected). Secrets only from env / `.env`. |
| `intents.py` | Rule-based router. Order matters: emergency → confirmation → control → specific commands → general question. |
| `assistant.py` | One handler per intent. All dependencies injected, so tests use fakes. |
| `speech.py` | Priority queue in front of the TTS engine: interrupt, flush, discard, de-duplicate. |
| `locales.py`, `i18n.py` | Every spoken sentence in `id` and `en`; a test enforces identical keys and placeholders. |
| `storage.py` | SQLite via SQLAlchemy 2.0: face embeddings (raw float vectors) and preferences. |
| `downloads.py` | Atomic downloads of Piper voices and face models into `models/`. |
| `hal/` | Hardware adapters with lazy imports: camera (on-demand, or `ContinuousCamera` reading on a background thread for the preview), speech input, Piper / pyttsx3 output, IP location, Windows console. |
| `monitor.py` | What the assistant heard, saw and said, as plain data (`Mark`: box + label + kind). No drawing, no OpenCV. |
| `preview.py` | `--preview`: draws marks on frames (`annotate`) and shows them in an OpenCV window on its own thread. |
| `services/vision.py` | Fresh frame capture, "can't see" checks, YOLOv8 detection, EasyOCR. |
| `services/spatial.py` | Detection → clock direction + rough distance. |
| `services/faces.py` | Face detection, embeddings, matching; YuNet + SFace (default) or dlib. |
| `services/imaging.py` | Downscale + JPEG-encode a frame before it goes to a vision model. |
| `services/llm.py` | OpenAI-compatible client: `answer()` for questions, `look()` for images; local-endpoint check. |
| `services/navigation.py` | Geocoding, routing and spoken turn instructions. |

## Two speeds of seeing

| | Fast path | Detailed path |
| --- | --- | --- |
| Commands | "apa di depan", "benda apa saja", "baca tulisan", "siapa ini" | "jelaskan lebih detail", "baca dokumen", "lihat, …" |
| Engine | YOLOv8n, EasyOCR, YuNet + SFace | Vision-language model (default `gemma3:4b` via Ollama) |
| Runs | Always on this machine | Local by default; cloud only if allowed and announced |
| Output | Structured: what, clock direction, distance | Free sentences, document text, answers |
| Latency | Sub-second to a few seconds (CPU) | Several seconds; the first request also loads the model |
| Future use | Basis for continuous hazard detection (Fase 2) | On-demand understanding only — never for safety |

The detailed path sends **one** downscaled JPEG (`llm.image_max_side`) as a
base64 data URL in the standard OpenAI `image_url` format, so any compatible
server works. The system prompt tells the model to describe only what is
visible, say when something is unclear, and never claim a path is clear or
something is safe. Obstacle questions are never routed to it.

## Where things are: clock directions and distance

`services/spatial.py` turns a detection box into a `Placement`:

- **Direction:** the box centre's horizontal angle from
  `camera.horizontal_fov_deg`, rounded to a clock hour (12 = ahead).
- **Distance:** pinhole model,
  `distance = typical_height × focal_length_px / box_height_px`, with a
  typical height per object class (person 1.65 m, chair 0.9 m, car 1.5 m, …).
  Classes without a predictable height get a direction only.
- **Cut off** by the top or bottom of the frame: the box height says
  nothing about distance. If it fills ≥ 60 % of the frame height it is
  *very close* (no number), otherwise it gets a direction only.
- **People:** when a detected face lies inside the person box, the distance
  comes from the face height (`vision.face_height_m`, 0.21 m) — if the face
  is at least 40 px tall, or if the body gave no distance (cut off). A webcam
  only sees a standing adult head to toe beyond ~2.5 m, so this is what
  gives close people a number.
- Under 1 m is spoken as *less than 1 meter*. Objects of the same kind in
  the same direction are grouped ("2 orang di jam 12, yang terdekat …"),
  nearest group first; the rest of the scene is summarised as a count.

Accuracy is roughly ±30 %; everything is spoken with *about*. Calibration:
[CONFIGURATION.md](CONFIGURATION.md#calibrating-distances).

## Speech priorities

| Priority | Used for | Behaviour |
| --- | --- | --- |
| `CRITICAL` | Emergency (later: hazard alerts) | Interrupts whatever is playing and drops queued chatter |
| `HIGH` | The direct answer to the last command | Normal answer |
| `NORMAL` | Hints and follow-up notices | Can be cut off by an answer |
| `LOW` | Acknowledgements ("Sebentar…") | Discarded once the real answer is ready |

The privacy notice "sending the photo to the internet" is `HIGH`, queued
before the answer: equal priorities never interrupt each other and play in
order, so the answer can never jump ahead of the notice.

## Data flows and privacy

| Data | Leaves the machine? | Notes |
| --- | --- | --- |
| Microphone audio | Yes — Google speech recognition | Offline STT planned |
| Camera frames | No, except the detailed path to a **cloud** VLM | Needs `llm.allow_images_to_cloud: true`; announced every time; `--check` shows "blocked" otherwise |
| Face embeddings | No | `data/aiforus.db`, raw float64 vectors; encryption planned |
| General questions | Only to a hosted LLM if configured | Local Ollama by default |
| IP / destinations | Yes — ipinfo.io, Nominatim, OSRM | Nominatim gets an identifying User-Agent as its policy requires |

A local endpoint is `localhost`, `*.local`, or a loopback / private /
link-local IP address (`is_local_endpoint`).

## Key decisions

| Decision | Why |
| --- | --- |
| **Rule-based intent router, LLM only for unknown questions** | Safety-relevant routing (emergency, exit) must be predictable and testable. The LLM never decides what the assistant *does*. |
| **Emergency is matched first, on the raw utterance** | A missed emergency is far worse than a false one, and a false one only speaks guidance. |
| **Exit requires the whole phrase plus confirmation** | The old substring router shut the app down on "is my friend here" ("friend" contains "end"). |
| **Priority speech queue with interruption** | A future hazard alert must cut off whatever is being read. |
| **Half-duplex listening** | With a real microphone the assistant would otherwise transcribe its own voice. Barge-in needs a wake word or echo cancellation (planned). |
| **Hardware abstraction layer with lazy imports** | Swap laptop webcam → glasses camera by writing one adapter. Tests and CI run without OpenCV, PyAudio, ML models or a GPU. |
| **Piper as the default voice** | Natural offline Indonesian voice; Windows rarely ships one pyttsx3 can use. Audio is played in ~50 ms slices so "diam" stops it almost immediately. |
| **"I can't see" is different from "I see nothing"** | Dark or covered frames are reported explicitly; "nothing detected" must never be mistaken for "all clear". |
| **Clock directions + rough distance** | Orientation & mobility training uses clock directions. Distance is always "about" and never a safety guarantee. |
| **Face recognition with YuNet + SFace (OpenCV DNN)** | ~40 MB of ONNX models (~10 MB int8), no C++ build, runs on Raspberry Pi / Jetson / phones — the same code path as the future edge device. Embeddings are L2-normalised so one Euclidean threshold (1.128) equals SFace's cosine threshold (0.363). dlib stays as a desktop-only backend; embeddings of different models are stored separately. |
| **Multi-sample enrollment** | One command saves several samples from different frames; one blurry frame no longer fails enrollment and recognition is more robust. |
| **One OpenAI-compatible client for LLM and VLM** | No vendor lock-in: local Ollama today, a hosted provider later by changing `base_url`. |
| **Presence checks are structured, the sentence is ours** | A 4B vision model said "Tidak terlihat. Ada kunci di atas meja" in one answer. For "is there …?" it only returns JSON (`visible`, `clock`, `detail`, JSON mode where supported); `services/presence.py` turns anything unreadable or self-contradictory into "not sure", and the assistant composes the sentence. Works with any model size, including small edge models. |
| **Images stay local unless explicitly allowed** | Photos of a user's home, documents and people are sensitive. Cloud use is opt-in and announced every time. |
| **Face encodings as raw float64 in SQLite** | `pickle.load` on a replaceable file can execute code. Names are case-insensitive; enrollment refuses frames with several faces. |
| **Typed config, secrets only from env** | Typos in `config.yaml` fail at startup; API keys never live in the repo. |
| **Every sentence in `locales.py`** | Indonesian first, English kept in sync; a test enforces it. |

## Live preview

```
 Assistant ──heard / said / answered(frame, marks)──► Monitor (protocol, monitor.py)
                                                         └─ PreviewWindow (preview.py, own thread)
 ContinuousCamera ──latest()──► PreviewWindow ──annotate()──► cv2.imshow
        └──capture()──► VisionService (the assistant gets a frame taken after its request)
```

- The assistant only **reports** (`Monitor`), so another display — a phone
  app later — can replace the window without touching the assistant. A
  failing display is logged and ignored; it can never break an answer.
- With `--preview` one `ContinuousCamera` thread reads the webcam and feeds
  both the window and the assistant; without it the camera is read only on
  demand (camera light off between commands).
- Live detection is throttled (`PreviewWindow.DETECT_INTERVAL_S`, 0.3 s) and
  shares the detector's lock with the assistant, which waits at most one
  detection.
- After each answer the exact photo it was based on is held on screen for
  4 s with the marks the assistant used.

## Path to smart glasses

The glasses become new `hal/` adapters — a camera that yields frames, a
microphone that yields utterances, a speaker that plays text — while the
router, assistant and services stay unchanged. Candidates (undecided):
Mentra Live, Ray-Ban Meta with Meta's device toolkit, Brilliant Labs Frame.
Compute stays on a phone or edge board; face models are already sized for
it (`face.quantized: true`).

## Known limitations (tracked in the roadmap)

- Speech recognition uses Google's online API; offline STT is planned.
- No barge-in: you can't interrupt by talking while it speaks (only after).
- No obstacle, traffic or hazard detection yet; sound-based detection from
  v1.1 was removed because it was not reliable (old code: tag
  `v1.1.0-legacy`).
- Distances are rough (lying objects, people facing away); depth estimation
  is planned. `vision.face_height_m` is not yet calibrated against real
  measurements.
- Vision-language models can hallucinate (wrong numbers, invented text).
  Answers about money or medicine must be double-checked.
- A local LLM only knows its training data (it named the previous
  Indonesian president in a test). It is given today's date and told to warn
  that changing facts may be out of date; live information (web search) is
  a separate, planned feature.
- EasyOCR misses small, distant or stylised text; "baca tulisan" then falls
  back to the vision model (`vision.ocr_fallback`).
- The preview window is not supported on macOS yet (OpenCV windows must run
  on the main thread there).
- With the default PyTorch install (CPU-only on Windows) YOLO and EasyOCR
  run on the CPU; using the GPU (CUDA build of PyTorch, VRAM shared with
  Ollama) is planned.
- Location is IP-based (kilometres off), so navigation is a demo until GPS
  from a phone is available. The public OSRM server only has a car profile.
- Emergency alerts are not sent anywhere yet; the assistant says so.
- The SQLite database (face encodings = biometric data) is not encrypted.
