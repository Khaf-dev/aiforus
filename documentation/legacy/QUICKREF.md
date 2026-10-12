# Quick Reference Guide

Fast lookup reference for common tasks and commands.

## Quick Start

```bash
# Setup (one-time)
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env

# Run application
python app.py

# Exit: Say "Goodbye" or "Exit"
```

---

## Common Commands

### Voice Commands

| Command                            | Action                    |
| ---------------------------------- | ------------------------- |
| "Describe my surroundings"         | Detailed scene analysis   |
| "What do you see?"                 | Brief environment summary |
| "Read text around me"              | Extract and read text     |
| "What objects are here?"           | Identify objects          |
| "Who do you see?"                  | Detect faces              |
| "Give me directions to [location]" | Navigate                  |
| "Goodbye" / "Exit"                 | Exit application          |

---

## Terminal Commands

### Setup & Installation

```bash
# Virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate  # Windows

# Dependencies
pip install -r requirements.txt
pip install --upgrade pip

# Specific packages
pip install torch torchvision transformers ultralytics
```

### Running Application

```bash
# Normal mode
python app.py

# Debug mode
python app.py --debug

# Test mode
python app.py --test
```

### Testing & Validation

```bash
# Import check
python -c "from app import VisionAssistant; print('OK')"

# Config validation
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Module test
python -c "from ai_modules.vision_processor import VisionProcessor; print('OK')"

# Database test
python -c "from database.db_handler import DatabaseHandler; print('OK')"
```

### Docker

```bash
# Build image
docker build -t vision-assistant:1.0 .

# Run container
docker run -d --name vision-assistant \
  -v $(pwd)/config.yaml:/app/config.yaml \
  vision-assistant:1.0

# View logs
docker logs -f vision-assistant

# Stop container
docker stop vision-assistant
docker rm vision-assistant

# Docker compose
docker-compose up -d
docker-compose logs -f
docker-compose down
```

---

## Configuration

### config.yaml - Key Settings

```yaml
# Application
app:
  debug: false # Set true for testing
  version: "1.0.0"

# AI/ML Models
ai:
  llm_provider: openai # Use 'local' for offline
  vision_model: yolov8n # Options: yolov8s, yolov8m, etc.
  device: cpu # Use 'cuda' for GPU

# Voice
speech:
  language: en # Language code
  speech_rate: 150 # Words per minute (50-300)
  use_google_tts: false # Use gTTS for online TTS

# Accessibility
accessibility:
  voice_feedback: true # Disable if only text needed
```

### .env - Environment Variables

```bash
# Required (no default)
OPENAI_API_KEY=sk-...

# Optional APIs
GOOGLE_MAPS_API_KEY=...
WEATHER_API_KEY=...

# Configuration overrides
SPEECH_LANGUAGE=en
DEVICE=cpu
DEBUG=false
```

---

## File Locations

| File                           | Purpose                         |
| ------------------------------ | ------------------------------- |
| `app.py`                       | Main application entry point    |
| `config.yaml`                  | Application configuration       |
| `.env`                         | Environment variables (secrets) |
| `requirements.txt`             | Python dependencies             |
| `ai_modules/`                  | Core AI modules                 |
| `features/`                    | High-level features             |
| `database/`                    | Database and models             |
| `database/vision_assistant.db` | SQLite database                 |
| `documentation/`               | All documentation files         |

---

## Troubleshooting Quick Fixes

| Problem                 | Quick Fix                                                         |
| ----------------------- | ----------------------------------------------------------------- |
| No sound                | Check system volume, verify speaker selected                      |
| Microphone not detected | Add user to audio group (Linux): `sudo usermod -a -G audio $USER` |
| Camera not working      | Check video permissions, list devices: `v4l2-ctl --list-devices`  |
| Module not found        | Activate venv, install: `pip install -r requirements.txt`         |
| Database locked         | Kill existing process: `pkill -f "python app.py"`                 |
| GPU not detected        | `python -c "import torch; print(torch.cuda.is_available())"`      |
| API key error           | Check .env file, verify `OPENAI_API_KEY` is set                   |
| Slow inference          | Switch to nano model, reduce resolution, use GPU                  |

---

## Performance Targets

| Operation           | Target    | Notes                                  |
| ------------------- | --------- | -------------------------------------- |
| Startup             | <5s       | First run slower due to model download |
| Voice recognition   | <2s       | Depends on speech length               |
| Object detection    | 100-200ms | CPU; 20-50ms with GPU                  |
| Response generation | <2s       | Uses OpenAI API                        |
| Text extraction     | 200-500ms | CPU-dependent                          |

---

## Development Workflow

### Adding New Voice Command

1. Add intent to `llm_handler.py` keywords
2. Create handler method in `app.py`
3. Call existing features or create new feature
4. Test with voice

**Example**:

```python
# llm_handler.py
'get_weather': ['weather', 'climate'],

# app.py
elif intent['action'] == 'get_weather':
    await self.get_weather()

async def get_weather(self):
    self.speech.speak("Fetching weather")
    # Implementation
```

### Adding New Vision Feature

1. Create method in `VisionProcessor`
2. Wrap in `features/`
3. Add to command router
4. Test with images

---

## System Requirements

### Minimum (Development)

- **CPU**: 2-core (i5/i7/Ryzen 5)
- **RAM**: 4GB
- **Storage**: 5GB (models cache)
- **Network**: Optional for local mode

### Recommended (Production)

- **CPU**: 4+ cores
- **RAM**: 8GB+
- **GPU**: NVIDIA RTX 2060+ (optional but recommended)
- **Storage**: 10GB SSD
- **Network**: For API calls

### Supported Platforms

- Windows 10+
- macOS 10.15+
- Linux (Ubuntu 18.04+, CentOS 7+)

---

## Key Dependencies

| Package                | Version  | Purpose          |
| ---------------------- | -------- | ---------------- |
| torch                  | 2.0.1+   | Deep learning    |
| transformers           | 4.31.0+  | NLP models       |
| ultralytics            | 8.0.124+ | YOLOv8           |
| opencv-python-headless | 4.8.0+   | Computer vision  |
| easyocr                | 1.7.0+   | Text recognition |
| speechrecognition      | 3.10.0+  | STT              |
| pyttsx3                | 2.90+    | Offline TTS      |
| openai                 | 1.0.0+   | LLM API          |
| sqlalchemy             | 2.0.19+  | Database ORM     |

---

## Environment Setup Verification

```bash
# Run these checks after setup

# 1. Python version
python --version  # Should be 3.8+

# 2. Virtual environment active
which python  # Should show venv path

# 3. Dependencies installed
pip list | grep torch

# 4. Core imports
python -c "import torch, cv2, transformers; print('✓')"

# 5. Database
python -c "from database.db_handler import DatabaseHandler; print('✓')"

# 6. Models can load
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

---

## API Quick Reference

### VisionAssistant

```python
from app import VisionAssistant
import asyncio

async def main():
    assistant = VisionAssistant()

    # Main loop
    await assistant.continuous_assistant()

asyncio.run(main())
```

### VisionProcessor

```python
from ai_modules.vision_processor import VisionProcessor

vp = VisionProcessor()
frame = vp.capture_image()
objects = await vp.detect_objects(frame)
texts = await vp.extract_text(frame)
faces = await vp.recognize_faces(frame)
```

### SpeechEngine

```python
from ai_modules.speech_engine import SpeechEngine

se = SpeechEngine()
command = await se.listen()
se.speak("Response text")
```

### LLMHandler

```python
from ai_modules.llm_handler import LLMHandler

llm = LLMHandler()
intent = await llm.understand_intent("user command")
response = await llm.generate_response("query")
```

### DatabaseHandler

```python
from database.db_handler import DatabaseHandler

db = DatabaseHandler()
prefs = db.get_user_preferences()
db.save_conversation(1, "input", "response")
db.close()
```

---

## Code Style Guide

### Python Standards

```python
# Type hints
def process_image(image: np.ndarray) -> List[Dict]:
    pass

# Async functions
async def describe_scene() -> str:
    pass

# Docstrings
def process_command(command: str):
    """Process voice command and route to appropriate handler.

    Args:
        command: User voice command text

    Returns:
        None (provides voice feedback)
    """
    pass

# Logging
import logging
logger = logging.getLogger(__name__)
logger.info("Starting process")
```

### Naming Conventions

- **Classes**: `PascalCase` (VisionProcessor)
- **Functions**: `snake_case` (capture_image)
- **Constants**: `UPPER_CASE` (MAX_RETRIES)
- **Private**: `_leading_underscore` (\_internal_method)

---

## Performance Tuning

### For Slower Devices

```yaml
# config.yaml - CPU/Low-End Hardware
ai:
  vision_model: yolov8n # Nano = fastest
  device: cpu # No GPU
  batch_size: 1 # Single image

speech:
  speech_rate: 200 # Faster speech
  use_google_tts: false # Local TTS (faster)

# Capture lower resolution
video:
  width: 320
  height: 240
```

### For Faster Devices

```yaml
# config.yaml - GPU/High-End Hardware
ai:
  vision_model: yolov8l # Large = more accurate
  device: cuda # GPU acceleration
  batch_size: 4 # Process 4 images

# Capture higher resolution
video:
  width: 1280
  height: 960
```

---

## Resources

| Resource   | Link                                       |
| ---------- | ------------------------------------------ |
| Python     | https://python.org                         |
| PyTorch    | https://pytorch.org                        |
| YOLOv8     | https://github.com/ultralytics/ultralytics |
| OpenCV     | https://opencv.org                         |
| OpenAI     | https://openai.com/api                     |
| SQLAlchemy | https://sqlalchemy.org                     |

---

## Documentation Links

- [README.md](../README.md) - Project overview
- [INSTALLATION.md](./setup/INSTALLATION.md) - Detailed setup
- [API.md](API.md) - API reference
- [ARCHITECTURE.md](ARCHITECTURE.md) - System design
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) - Common issues
- [DEPLOYMENT.md](DEPLOYMENT.md) - Production guide
- [CONTRIBUTING.md](./guidelines/CONTRIBUTING.md) - Development guidelines

---

## Common Bash Aliases

Add to shell profile (`.bashrc`, `.zshrc`, etc.):

```bash
alias va-run='cd ~/aiforus && source venv/bin/activate && python app.py'
alias va-test='cd ~/aiforus && source venv/bin/activate && python -m pytest tests/'
alias va-logs='tail -f ~/aiforus/logs/vision_assistant.log'
alias va-db-reset='rm ~/aiforus/database/vision_assistant.db'
alias va-deps='pip install --upgrade -r requirements.txt'
```

Usage: `va-run`, `va-test`, etc.

---

## Support & Issues

1. Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md) first
2. Review [INSTALLATION.md](./setup/INSTALLATION.md) setup steps
3. Search existing GitHub issues
4. Collect system info: `python info.py`
5. Open new issue with details

---

**Last Updated**: 2024-12-20
**Version**: 1.0.0
**Help**: See documentation folder for detailed guides
