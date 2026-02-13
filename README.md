# README.md

# Vision Assistant - AI-Powered Accessibility for the Visually Impaired

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Version: 1.1.0](https://img.shields.io/badge/Version-1.1.0-green.svg)](documentation/RELEASE_v1.1.md)
[![Status: Stable Release](https://img.shields.io/badge/Status-Development%20Stage-brightgreen)]()

## 🌟 Now With v1.1 Features!

**Vision Assistant v1.1** brings revolutionary accessibility features:

- 🌍 **8 Languages** - English, Indonesian, Spanish, French, German, Portuguese, Japanese, Mandarin Chinese
- 👁️ **Face Recognition + Training** - Learn who's who with voice commands
- 🔊 **3D Audio Localization** - Know where sounds come from with 8-directional awareness
- 🚨 **Intelligent Obstacle Detection** - Audio-based hazard warnings
- 🎯 **100+ Voice Commands** - Full voice control in all languages

[→ See v1.1 Release Notes](documentation/v.1.1/RELEASE_v1.1.md)

## Overview

**Vision Assistant** is an AI-powered voice-controlled visual assistance system designed to empower visually impaired individuals by providing real-time scene understanding, text recognition, object detection, navigation assistance, and intelligent audio awareness through natural voice interaction.

### Key Features v1.1

- 🎤 **Multi-Language Voice I/O** - 8 languages with dynamic switching
- 👁️ **Face Recognition** - Detect, recognize, and learn faces with voice commands
- 🔊 **Audio Localization** - 3D sound positioning and classification
- 🧠 **Intent Recognition** - Understand 100+ voice commands
- 📍 **Audio-Guided Navigation** - GPS + sound-based directions
- 🚨 **Emergency Alerts** - Multi-language emergency notifications
- 💾 **Persistent Data** - Face database, user preferences, history
- 🔄 **Full Voice Control** - No visual UI required

## Quick Start

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/Khaf-dev/aiforus.git
cd aiforus

# 2. Create virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (optional)
cp .env.example .env
# Edit .env with your API keys
```

### First Run

```bash
# English (default)
python app.py

# Indonesian
python app.py --lang=id

# Spanish
python app.py --lang=es
```

### Available Languages

| Code | Language         | Status          |
| ---- | ---------------- | --------------- |
| en   | English          | ✅ Default      |
| id   | Indonesian       | ✅ Full support |
| es   | Spanish          | ✅ Full support |
| fr   | French           | ✅ Full support |
| de   | German           | ✅ Full support |
| pt   | Portuguese       | ✅ Full support |
| ja   | Japanese         | ✅ Full support |
| zh   | Mandarin Chinese | ✅ Full support |

## Voice Commands v1.1

### Multi-Language (All languages)

- "Change language to Indonesian"
- "Switch to Spanish"
- "Speak French"

### Face Recognition

- "Enroll John" / "Register face as Sarah"
- "Who do you know?" / "Forget John"
- "Face statistics"

### Audio & Obstacles

- "What do you hear?" / "Detect sounds"
- "Check ahead" / "Detect obstacles"
- "Classify sound" / "What sound is that?"

### Vision (Classic)

- "Describe the scene" / "What do you see?"
- "Read any text" / "Detect objects"
- "Identify people" / "Where am I?"

[See All 100+ Commands](documentation/v.1.1/VOICE_COMMANDS.md)

## System Requirements

### Minimum

- **OS**: Windows 10+, macOS 10.14+, Ubuntu 18.04+
- **Python**: 3.8+
- **RAM**: 4GB (8GB recommended)
- **Storage**: 2GB (for ML models)
- **Microphone**: Required
- **Camera**: Optional (for vision features)

### Recommended

- **OS**: Windows 11, macOS 12+, Ubuntu 20.04+
- **Python**: 3.10+
- **RAM**: 8GB+
- **GPU**: NVIDIA (CUDA) for faster processing
- **Microphone**: External USB mic for audio localization

### Hardware Recommendations

- **CPU**: Intel i5/AMD Ryzen 5 or equivalent
- **GPU**: NVIDIA GPU with CUDA (optional, for faster processing)
- **RAM**: 8GB or more
- **Storage**: SSD (faster model loading)

## Project Structure

```
aiforus/
├── app.py                          # Main application entry point
├── config.yaml                     # Configuration file
├── requirements.txt                # Python dependencies
├── .env.example                    # Environment variables template
│
├── ai_modules/                     # Core AI/ML modules
│   ├── vision_processor.py         # Computer vision (YOLOv8, EasyOCR)
│   ├── speech_engine.py            # Voice I/O (pyttsx3, SpeechRecognition)
│   ├── llm_handler.py              # Language model (OpenAI/Local)
│   └── neural_core.py              # Model management
│
├── features/                       # Feature modules
│   ├── navigation.py               # GPS/directions
│   ├── object_detection.py         # Object recognition
│   ├── text_reader.py              # OCR pipeline
│   └── face_recognition.py         # Face detection
│
├── database/                       # Data persistence
│   ├── models.py                   # SQLAlchemy ORM models
│   └── db_handler.py               # Database operations
│
├── tests/                          # Testing
│   ├── validation.py               # Bootstrap validation
│   └── __init__.py
│
├── documentation/                  # Project documentation
│   ├── README.md                   # This file
│   ├── INSTALLATION.md             # Detailed setup guide
│   └── CONTRIBUTING.md             # Contribution guidelines
│
├── demo_features.py                # Feature demonstration
├── demo_exit_feature.py            # Exit feature demo
├── test_features.py                # Feature testing
│
├── LICENSE                         # MIT License
└── .github/
    └── copilot-instructions.md     # AI agent guidelines
```

## Technology Stack

### Core Libraries

| Component           | Library                          | Version            |
| ------------------- | -------------------------------- | ------------------ |
| **Computer Vision** | YOLOv8, OpenCV, EasyOCR          | Latest             |
| **Speech**          | pyttsx3, SpeechRecognition, gTTS | 2.90+, 3.10+, 2.3+ |
| **Language Model**  | OpenAI, Transformers             | 1.0+, 4.31+        |
| **Deep Learning**   | PyTorch, TorchVision             | 2.0+, 0.15+        |
| **Backend**         | FastAPI, SQLAlchemy              | 0.100+, 2.0+       |
| **Configuration**   | PyYAML, python-dotenv            | Latest             |
| **Navigation**      | geopy, geocoder                  | Latest             |

### AI Models

- **Object Detection**: YOLOv8 (nano - ~6MB)
- **Text Recognition**: EasyOCR (English, extensible)
- **Face Detection**: OpenCV Cascade Classifier
- **Language Understanding**: GPT-3.5-turbo or local alternatives
- **Speech Synthesis**: pyttsx3 (offline) or Google TTS (online)

## Configuration

### Environment Variables (.env)

```env
# OpenAI Configuration (optional)
OPENAI_API_KEY=your_api_key_here

# Speech Configuration
SPEECH_LANGUAGE=en
SPEECH_RATE=150

# Device Configuration
DEVICE=cpu  # Use 'cuda' if GPU available

# Feature Flags
ENABLE_NAVIGATION=true
ENABLE_FACE_RECOGNITION=false
ENABLE_TEXT_EXTRACTION=true
ENABLE_OBJECT_DETECTION=true
```

### Application Configuration (config.yaml)

```yaml
app:
  name: "Vision Assistant"
  debug: true
  version: "1.0.0"

speech:
  language: "en"
  speech_rate: 150
  use_google_tts: false

ai:
  llm_provider: "openai" # or "local"
  vision_model: "yolov8n"
  text_model: "easyocr"
```

## Usage Examples

### Basic Usage

```python
python app.py
```

### Debug Mode

```python
python app.py --debug
```

### Test Import

```python
python app.py --test-import
```

### Run Tests

```python
python tests/validation.py
python test_features.py
```

## Troubleshooting

### Camera Not Working

```bash
# Linux: Install camera drivers
sudo apt install v4l2-ctl

# Check camera permissions
ls -l /dev/video*
sudo usermod -a -G video $USER
```

### Audio Issues

```bash
# Install audio libraries
pip install --upgrade pyttsx3 pyaudio
```

### Model Download Slow

The first run downloads ~2GB of models. Use offline mode or:

```bash
pip install --no-cache-dir -r requirements.txt
```

## Performance

### Expected Performance

- **Startup Time**: 2-3 seconds (after model cache)
- **Voice Command Response**: 1-2 seconds
- **Object Detection**: 100-200ms per image (CPU)
- **Text Recognition**: 200-500ms per image (CPU)
- **Memory Usage**: 300-500MB idle, 800MB-1GB during processing

### Optimization Tips

1. Use GPU if available: Set `DEVICE=cuda`
2. Use smaller YOLOv8 variant for faster detection
3. Batch process images for efficiency
4. Cache frequently accessed data

## API Reference

### VisionAssistant Class

```python
assistant = VisionAssistant()
await assistant.describe_environment(detailed=True)
await assistant.read_text_around()
await assistant.identify_objects()
await assistant.recognize_faces()
```

### SpeechEngine

```python
from ai_modules.speech_engine import SpeechEngine
engine = SpeechEngine()
engine.speak("Hello!")
command = await engine.listen()
```

### LLMHandler

```python
from ai_modules.llm_handler import LLMHandler
llm = LLMHandler(use_openai=True)
intent = await llm.understand_intent("What do you see?")
response = await llm.generate_response(query)
```

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](documentation/guidelines/CONTRIBUTING.md) for guidelines.

## License

This project is licensed under the MIT License - see [LICENSE](LICENSE) file for details.

## Authors

- **Khaf-dev** - Initial development and architecture
- Contributors welcome! See [CONTRIBUTING.md](documentation/guidelines/CONTRIBUTING.md)

## Acknowledgments

- **YOLOv8** by Ultralytics for object detection
- **EasyOCR** for text recognition
- **PyTorch** community for deep learning framework
- **OpenAI** for language models
- Community for accessibility feedback and testing

## Roadmap

### v1.1 (Planned)

- [ ] Mobile app support (iOS/Android)
- [ ] Improved face recognition with training
- [ ] Multi-language support
- [ ] Enhanced navigation with real-time obstacles
- [ ] Sound localization

### v1.2 (Future)

- [ ] Edge device optimization (Raspberry Pi)
- [ ] Offline-first architecture
- [ ] Custom voice training
- [ ] Integration with smart home devices
- [ ] Biometric authentication

## Support

- 📧 Email: rifyatkaffa@gmail.com
- 💬 GitHub Issues: [Report bugs](https://github.com/Khaf-dev/aiforus/issues)
- 📚 Documentation: [Full docs](documentation/)
- 🐛 Bug reports: Include OS, Python version, error logs

## FAQ

**Q: Does it work without internet?**  
A: Yes! Core vision and speech features work offline. OpenAI features require internet.

**Q: Can I use it without a camera?**  
A: Yes! Chat features work without camera. Vision features are optional.

**Q: Is it GDPR/Privacy compliant?**  
A: Data is stored locally by default. No data is sent to servers without explicit consent.

**Q: How can I improve accuracy?**  
A: Better lighting, clear speech, and positioned camera help significantly.

**Q: Can I train custom models?**  
A: Yes! See documentation for fine-tuning guides.

## Security & Privacy

- All voice data processed locally
- Camera feed never stored by default
- Database encrypted at rest (configurable)
- No telemetry without consent
- GDPR/CCPA compliant

---

**Made with ❤️ for accessibility and inclusion**

Last Updated: February 2026  
Version: 1.1.0
