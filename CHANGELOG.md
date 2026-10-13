# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/).

## [Unreleased]

### Added
- **Live preview** (`--preview`): a camera window with boxes and labels
  ("kursi | jam 1 | ~2 m", names on faces), what was heard and said, and for
  4 s after each reply the exact photo it was based on. One background
  camera reader (`ContinuousCamera`) feeds the window and the assistant. The
  assistant reports through a `Monitor` protocol, so a phone display can
  replace the window later. Nothing is saved.
- People are placed: *"Aku melihat 2 wajah. Kaffa di jam 12, sekitar 1 meter.
  Orang yang belum aku kenal di jam 2, sekitar 3 meter."* Known people first,
  nearest first; more than two strangers are counted.
- When "baca tulisan" finds no text, the assistant looks again at the same
  photo with the vision model (`vision.ocr_fallback: vlm`, default), or only
  suggests "baca dokumen" (`hint`), or neither (`off`).
- **Detailed vision with a vision-language model** (Fase 1B): "jelaskan
  lebih detail", "baca dokumen / surat / menu", and "lihat, <pertanyaan>"
  ("lihat, ini uang berapa?"). Uses the LLM endpoint (`llm.vision_model`,
  default = `llm.model`); the default config points at local Ollama with
  `gemma3:4b`. Photos are downscaled (`llm.image_max_side`) and JPEG-encoded.
  Images never go to a cloud endpoint unless `llm.allow_images_to_cloud` is
  true, and then every request is announced. The prompt forbids claiming a
  path is clear or anything is safe; obstacle questions keep the honest
  "not available" answer.
- **Clock directions and rough distances** (Fase 1A): "Kursi di jam 1,
  sekitar 2 meter. 2 orang di jam 12, yang terdekat sekitar 3 meter."
  Bearing from the box centre and `camera.horizontal_fov_deg`; distance from
  the pinhole model and a typical height per object class; boxes cut off by
  the frame are reported as "sangat dekat" without a number. Nearest first,
  the rest summarised.
- People are measured by the size of their face when it is visible
  (`vision.face_height_m`, default 0.21 m), so someone 1–2.5 m away — whose
  body doesn't fit in a webcam frame — gets a distance instead of
  "sangat dekat". Small faces (far away) fall back to body height.
- **Face recognition with OpenCV YuNet + SFace** (default `face.backend:
  opencv`): ONNX models (~40 MB, or ~10 MB with `face.quantized: true`) that
  run on edge devices, no dlib/C++ build needed. dlib remains available as
  `face.backend: dlib`. Embeddings are stored per model, so switching
  backends never mixes incompatible vectors.
- Piper neural TTS (`piper` extra): natural offline Indonesian voice
  (`id_ID-news_tts-medium`) and English voice (`en_US-lessac-medium`),
  streamed per sentence and interruptible within ~50 ms.
- `python -m aiforus --download-models` downloads the Piper voices and face
  models into `models/` (atomic, skips files already present).
  `--download-voices` still works as an alias.
- `speech.engine` setting: `auto` (Piper if available, else pyttsx3),
  `piper` or `pyttsx3`. `--check` shows which engine and voices are in use.
- Documentation: `documentation/CONFIGURATION.md` (every setting, LLM/VLM
  providers, distance calibration) and `documentation/TROUBLESHOOTING.md`.

### Changed
- General questions work with any OpenAI-compatible LLM: `llm.base_url`
  (e.g. Ollama at `http://localhost:11434/v1`, local and free) and
  `LLM_API_KEY` (any provider; `OPENAI_API_KEY` still accepted). No key is
  needed for local servers. `--check` probes the server and model.
  `llm.timeout_s` default raised to 30 s for CPU-only local models.
- Face enrollment keeps grabbing frames for up to `face.enroll_timeout_s`
  (default 4 s) and saves `face.enroll_samples` (default 3) samples from
  different frames in one command. A single blurry or empty frame no longer
  fails enrollment, and several samples make recognition more robust.
- `face.match_threshold` now defaults to the backend's recommended value
  (SFace 1.128 ≈ cosine 0.363; dlib 0.55).
- The `vision` extra pins `opencv-python<5`: the YuNet/SFace models in use
  are the OpenCV 4.x DNN versions.
- README, ARCHITECTURE and VOICE_COMMANDS rewritten for the current feature
  set (VLM, face-based distance, data flows, project layout, example
  dialogue). `requirements.txt` installs the recommended extras instead of
  `all`, so it no longer tries to build dlib.

### Fixed
- "ini siapa", "itu siapa", "siapa orang ini" now recognise faces instead of
  going to the LLM (found in the first Windows field test).
- Image requests use `llm.vision_timeout_s` and are not retried: the first
  request (which loads the model) was cut off at the 30 s chat timeout and
  sent again.
- The vision model said "di 3 jam" ("in 3 hours"); the clock-direction
  instruction is now written in the reply language ("di arah jam 3").
- General answers: the LLM is told today's date, to warn that changing facts
  (office holders, prices, news) may be out of date, and not to ask
  follow-up questions.
- The "sending the photo to the internet" notice could be spoken after the
  answer; it is now always before it.
- English: "I see 1 faces" → "I see one face".
- "ada berapa orang" / "how many people" counts with the camera instead of
  going to the LLM (as the whole question only) and answers with the number
  first: "Aku melihat 2 orang." With nobody in view: "Aku tidak melihat
  orang di kamera" (never "there is nobody").
- The LLM no longer announces the date or adds "may be out of date" to
  answers that don't need it.
- The vision model only uses clock positions 9 to 3 (it had said "jam 6",
  which is behind the user) and is told the user is not in the photo.
- A flaky speech-queue test (race in the fake TTS and in the test itself).
- Console no longer shows comtypes cache logs and harmless torch warnings
  (still visible with `--debug`).
- English "1 meters" → "1 meter".
- Windows: the assistant no longer freezes until Enter is pressed after a
  click in the console window (QuickEdit mode is disabled while it runs and
  restored on exit).

## [0.2.0] — Fase 0: foundation

A rewrite of the application core. The version goes *down* from 1.1.0 on
purpose: 1.1.0 advertised features that did not work, and this release is an
honest pre-1.0 research prototype.

### Safety
- Emergency is matched first and always wins. A bare "tolong" / "help me" is
  now an emergency (it used to open the help menu).
- Emergency no longer says "help is on the way": it says alerts can't be
  sent yet, tells the user to call 112 and gives the approximate location.
- Exiting needs the whole phrase and a spoken confirmation. Substring
  matching used to quit on "is my friend here" ("friend" contains "end").
- Dark, covered or missing cameras are reported as "I can't see", never as
  "nothing in front of you".
- Sound localization and echo obstacle detection were removed (they returned
  arbitrary directions and a constant 1.37 m obstacle).
- The full v1.1 code and docs remain available at the `v1.1.0-legacy` tag.
- Navigation always reminds the user that obstacles aren't detected and
  that IP-based location is approximate.

### Added
- `aiforus` package: typed config, i18n catalog (id/en), deterministic intent
  router, prioritised interruptible speech queue, hardware abstraction layer,
  services for vision, faces, navigation and LLM answers.
- `python -m aiforus` CLI with `--text`, `--mute`, `--lang`, `--check`.
- Turn-by-turn instructions from OSRM maneuvers, in Indonesian and English.
- Indonesian names for all 80 detectable object classes.
- pytest suite (no hardware needed), ruff, CI on Python 3.10–3.13.

### Changed
- Languages: Indonesian (default) and English. The other six languages of
  1.1.0 only changed the speech-recognition locale; all replies were English.
- Face data moved from a pickle file to SQLite (`data/aiforus.db`), stored as
  raw float vectors. Enrollment refuses frames with more than one face.
- Packaging moved to `pyproject.toml` with optional extras.
- The LLM is only used for general questions, never for command routing.

### Removed
- `ai_modules/`, `features/`, `database/`, `api_integration/`, `utils/`,
  `deploy.py`, `setup.py`, hardware-dependent test scripts and the unused
  conversation/scene logging tables (no transcripts are stored).
- Dependencies no longer needed: transformers, langchain, fastapi, alembic,
  geopy, geocoder, gTTS.

### Migration
- Faces enrolled with 1.1.0 (`database/face_encodings.pkl`) are not imported;
  enroll them again. The old `vision_assistant.db` is no longer used.

## [1.1.0] - 2026-02-11

### Added

#### Phase 1: Multi-Language Support

- **8 Language Support**: English, Indonesian, Spanish, French, German, Portuguese, Japanese, Mandarin Chinese
- **Dynamic Language Switching**: Change language via voice command at runtime
- **Language-Specific Speech Recognition**: Google Speech Recognition with language codes
- **Multi-Provider TTS**: Google TTS (online) + pyttsx3 (offline) for all languages
- **Command-Line Language Selection**: `python app.py --lang=id` for Indonesian
- **Configuration-Driven Management**: All languages configurable in `config.yaml`
- **Voice Feedback in Native Language**: All responses in user's selected language
- **Test Suite**: `test_multilingual.py` for validation

#### Phase 2: Intelligent Face Recognition with Training

- **Face Detection**: HOG (fast) and CNN (accurate) models
- **Face Recognition**: Compare detected faces against known faces
- **Face Enrollment/Training**: Learn new faces with voice commands ("Enroll John")
- **Multiple Samples Per Person**: Store up to 10 training samples per person
- **Persistent Face Database**: Automatic save/load with pickle serialization
- **Face Management**: List enrolled people, remove/forget people
- **Confidence Scoring**: Accuracy reporting for recognized faces
- **Database Models**: New `Person` and `FaceEncoding` ORM models
- **Voice Commands**: Enrollment, management, statistics
- **Test Suite**: `test_face_recognition.py` for validation

#### Phase 3: 3D Audio Localization & Obstacle Detection

- **Sound Detection**: Real-time audio event detection above noise floor
- **Sound Localization**: 8-directional compass output (Front, Right, Back, Front-Left, etc.)
- **Distance Estimation**: Estimates distance to sound sources (0.5-10m range)
- **Obstacle Detection**: Audio echo analysis for detecting barriers/obstacles
- **Automatic Warnings**: Alerts when obstacles detected within threshold (default 2m)
- **Sound Classification**: Identifies sound types (speech, alarms, doors, ambient)
- **Frequency Analysis**: STFT-based frequency domain analysis
- **Auto-Localization**: Beamforming and phase-shift methods
- **Navigation Integration**: Audio-guided directions using sound cues
- **Voice Commands**: "What do you hear?", "Check ahead", "Classify sound"
- **Test Suite**: `test_sound_localization.py` for validation

### Changed

- **NavigationAssistant**: Enhanced with audio guidance methods and sound integration
- **VisionAssistant**: Added SoundLocalizer initialization and audio command handlers
- **SpeechEngine**: Full YAML configuration support with language profiles
- **VisionAssistant.**init****: Now accepts optional `language` parameter
- **app.py**: Extended with `_handle_face_enrollment()`, `_handle_face_management()`, `_handle_audio_assistance()` methods
- **config.yaml**: Added `sound_localization` section with 40+ settings; enhanced `speech` section; enhanced `face_recognition` section

### New Files

- `ai_modules/sound_localization.py` - Complete audio processing and localization module
- `documentation/RELEASE_v1.1.md` - Official v1.1 release notes
- `documentation/VOICE_COMMANDS.md` - Comprehensive voice commands reference
- `documentation/CONFIG_GUIDE.md` - Detailed configuration guide
- `test_multilingual.py` - Multi-language feature tests
- `test_face_recognition.py` - Face recognition feature tests
- `test_sound_localization.py` - Audio localization feature tests

### Documentation

- **Voice Commands Reference**: 100+ categorized commands with examples
- **Configuration Guide**: Detailed settings for all 3 features
- **Architecture Documentation**: Updated system design docs
- **Troubleshooting Guide**: Common issues and solutions
- **Release Notes**: Complete v1.1 feature overview

### Dependencies (New)

- `librosa>=0.10.0` - Audio analysis and feature extraction
- `scipy>=1.10.0` - Signal processing utilities
- Enhanced `pyaudio` support for audio input

### Performance Improvements

- Optimized audio chunk processing (~100ms detection)
- Efficient face encoding lookup (<50ms per match)
- Streamlined language switching (<500ms)
- Reduced memory footprint for audio processing

### Infrastructure

- Enhanced configuration system with YAML validation
- Improved error handling for audio/hardware issues
- Better logging for debugging
- Cross-platform audio support

---

## [1.0.0] - 2026-02-09

### Added

#### Core Features

- **Vision Processing Pipeline**
  - Object detection using YOLOv8 (nano model)
  - Text extraction using EasyOCR
  - Face detection using OpenCV Haar cascades
  - Scene description with context awareness
  - Detailed vs. brief environment analysis

- **Voice Interaction System**
  - Speech-to-text using Google Speech Recognition
  - Text-to-speech with dual providers (pyttsx3 offline + gTTS online)
  - Multi-language support (configurable)
  - Adjustable speech rate (50-300 WPM)
  - Voice feedback for all operations

- **Language Model Integration**
  - OpenAI GPT integration for intelligent responses
  - Local keyword-based intent recognition fallback
  - Intent classification and parameter extraction
  - Context-aware response generation
  - 8 core intent types (describe_scene, read_text, etc.)

- **Navigation Assistance**
  - Current location retrieval
  - Route planning and directions
  - Nearby location discovery
  - GPS-based assistance

- **Database Persistence**
  - SQLAlchemy ORM with SQLite backend
  - User preference storage
  - Conversation history tracking
  - Scene memory for location context
  - Object detection history

- **Configuration System**
  - YAML-based application configuration
  - Environment variable support (.env)
  - Runtime parameter override capability
  - Secure API key management

#### Exit Command Recognition

- Recognizes 8+ goodbye variations: "goodbye", "bye", "exit", "quit", "stop", "turn off", "shut down", "close"
- Graceful shutdown with resource cleanup
- Voice confirmation before exit

#### Accessibility Features

- Voice-first interface (no visual UI required)
- Audio-only operation for complete accessibility
- Customizable speech rate and language
- Offline-capable core features

### Infrastructure

#### Environment Setup

- Python 3.8+ support
- Virtual environment configuration
- Automated dependency management
- Cross-platform support (Windows, macOS, Linux)

#### Dependencies (Core)

- PyTorch 2.0.1+ (deep learning framework)
- Transformers 4.31.0+ (NLP models)
- YOLOv8 (ultralytics 8.0.124+)
- OpenCV 4.8.0+
- EasyOCR 1.7.0+
- SpeechRecognition 3.10.0+
- pyttsx3 2.90+ (offline TTS)
- gTTS 2.3.2+ (online TTS)
- FastAPI (backend framework)
- SQLAlchemy 2.0.19+ (ORM)
- OpenAI 1.0.0+ (LLM API)

#### Development Tools

- Black (code formatting)
- Flake8 (linting)
- mypy (type checking)
- pytest (testing framework)

### Documentation

#### User Documentation

- **README.md** - Project overview, features, quick start, troubleshooting
- **INSTALLATION.md** - Platform-specific setup guide with system requirements
- **API.md** - Complete API reference with code examples
- **ARCHITECTURE.md** - System design and module relationships
- **CONTRIBUTING.md** - Development guidelines and contribution workflow
- **LICENSE** - MIT License

#### Internal Documentation

- `.github/copilot-instructions.md` - Agent onboarding guide
- Inline code documentation with docstrings
- Configuration examples (.env.example)

### Initial File Structure

```
ai_modules/
├── vision_processor.py
├── speech_engine.py
├── llm_handler.py
├── neural_core.py
└── __init__.py

features/
├── navigation.py
├── object_detection.py
├── text_reader.py
├── face_recognition.py
└── __init__.py

database/
├── models.py (ORM models)
├── db_handler.py
└── __init__.py

api_integration/
└── __init__.py

tests/
└── validation.py

app.py (main application)
config.yaml (configuration)
requirements.txt (dependencies)
.env.example (environment template)
README.md
INSTALLATION.md
API.md
ARCHITECTURE.md
CONTRIBUTING.md
LICENSE
```

### Fixed Issues

#### Error Resolution

1. **Missing ultralytics package** - Added to requirements.txt
2. **image-to-text pipeline deprecated** - Replaced with manual inference
3. **Speech rate attribute error** - Fixed initialization order
4. **Database schema mismatch** - Updated models with required fields
5. **OpenAI API deprecation** - Migrated to new client-based API (1.0.0+)

### Known Limitations

- Advanced face recognition (identification) uses placeholder implementation
- Cloud integrations (Google Maps, Weather) are optional
- Mobile deployment requires optimization
- Model download required on first run (~1GB)
- Requires camera and microphone for full functionality

### Performance Metrics

- **Startup Time**: 2-3 seconds after initialization
- **Object Detection**: 100-200ms per image (CPU)
- **Voice Recognition**: 1-2 seconds
- **Response Generation**: <2 seconds average
- **Memory Usage**: <500MB idle, <1GB during processing

### Platform Support

- **Windows 10+** - Full support
- **macOS 10.15+** - Full support
- **Linux (Ubuntu 18.04+)** - Full support
- **iOS/Android** - Planned for future release

### Security

- API keys stored in .env (not committed)
- HTTPS for all external API calls
- Local data storage option
- No automatic cloud sync without user consent

---

## [0.9.0] - Pre-Release (Unreleased)

### Initial Development

- Project structure established
- Core modules skeleton
- Async architecture design
- Configuration framework

---

## Future Roadmap

### [1.1.0] - Planned

#### Features

- Advanced face recognition and identification
- Real-time scene understanding with AI
- Multi-user support with profiles
- Conversation context persistence
- Emotion detection from voice

#### Improvements

- Mobile app deployment (iOS/Android)
- Model quantization for faster inference
- Battery optimization for mobile
- Improved offline capabilities

#### Infrastructure

- Docker containerization
- Cloud deployment option
- CI/CD pipeline with GitHub Actions
- Automated testing suite

### [1.2.0] - Planned

#### Accessibility Enhancements

- Braille output support
- Multiple TTS voice options
- Haptic feedback (mobile)
- Customizable audio profiles

#### Features

- Document scanning and reading
- Color detection and description
- Receipt and bill reading
- Barcode/QR code scanning

### [2.0.0] - Future

#### Major Features

- Multi-modal input (voice + touch)
- Real-time video processing
- Advanced neural networks
- Edge computing optimization

#### Deployment

- Full cloud architecture
- Federated learning
- Cross-platform synchronization
- Enterprise features

---

## Contributing

See [CONTRIBUTING.md](../CONTRIBUTING.md) for details on how to contribute to this changelog.

### Guidelines for Changes

- Use present tense ("Add feature" not "Added feature")
- Reference issues and pull requests liberally
- Group changes by category (Added, Changed, Fixed, Removed, etc.)
- Maintain semantic versioning

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/):

- **MAJOR** version for incompatible API changes
- **MINOR** version for new functionality (backwards compatible)
- **PATCH** version for bug fixes

---

## See Also

- [README.md](/README.md) - Project overview
- [CONTRIBUTING.md](../guidelines/CONTRIBUTING.md) - How to contribute
- [API.md](../API.md) - API reference
- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
