# Installation Guide

Complete step-by-step installation guide for Vision Assistant on Windows, macOS, and Linux.

## Table of Contents

1. [System Requirements](#system-requirements)
2. [Pre-Installation Checklist](#pre-installation-checklist)
3. [Windows Installation](#windows-installation)
4. [macOS Installation](#macos-installation)
5. [Linux Installation](#linux-installation)
6. [Post-Installation Verification](#post-installation-verification)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

---

## System Requirements

### Minimum Requirements

| Component   | Minimum               | Recommended       |
| ----------- | --------------------- | ----------------- |
| **CPU**     | 2-core (i5/Ryzen 5)   | 4-core or better  |
| **RAM**     | 4 GB                  | 8 GB+             |
| **Storage** | 5 GB free             | 10 GB SSD         |
| **Network** | Optional (local mode) | For full features |
| **GPU**     | None                  | NVIDIA RTX 2060+  |

### Supported Python Versions

- **Python 3.8** - Minimum supported
- **Python 3.9** - Recommended
- **Python 3.10** - Fully supported
- **Python 3.11** - Fully supported
- **Python 3.12** - Supported

### Supported Operating Systems

- **Windows 10/11** - Full support
- **macOS 10.15+** - Full support (Intel and Apple Silicon)
- **Linux** - Ubuntu 18.04+, CentOS 7+, Debian 10+, Fedora 30+

### Optional Hardware

- **Camera** - For vision features (USB camera supported)
- **Microphone** - For speech input (built-in or USB supported)
- **Speaker/Headphones** - For audio output
- **GPU** - NVIDIA with CUDA for acceleration

---

## Pre-Installation Checklist

### Before You Begin

- [ ] System meets minimum requirements
- [ ] Python 3.8+ installed (`python --version`)
- [ ] pip is available (`pip --version`)
- [ ] At least 5 GB free storage
- [ ] Internet connection (first run only, for model download)
- [ ] Administrator/sudo access (for system libraries on Linux)

### Check Python Installation

```bash
# Windows/macOS/Linux
python --version
python -m pip --version

# If python not found, try
python3 --version
python3 -m pip --version
```

**Expected Output**:

```
Python 3.8.0 or higher
pip X.Y.Z from ...
```

### Download Vision Assistant

```bash
# Clone repository
git clone https://github.com/Khaf-dev/aiforus.git
cd aiforus

# Or download ZIP
# Extract to desired location
cd aiforus
```

---

## Windows Installation

### Step 1: Install Python (if needed)

**Option A: Direct Download**

1. Visit [python.org](https://www.python.org/downloads/)
2. Download Python 3.11 or later
3. Run installer
4. **IMPORTANT**: Check "Add Python to PATH"
5. Click "Install Now"

**Option B: Microsoft Store**

```powershell
# In PowerShell
winget install Python.Python.3.11
```

**Verify Installation**:

```powershell
python --version
```

### Step 2: Create Virtual Environment

```powershell
# Open PowerShell in project directory
# Navigate to aiforus folder

# Create virtual environment
python -m venv venv

# Activate virtual environment
venv\Scripts\activate

# Expected: (venv) prefix in terminal
```

**Troubleshooting Activation**:

```powershell
# If activation fails, run:
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then try activation again
venv\Scripts\activate
```

### Step 3: Upgrade pip

```powershell
python -m pip install --upgrade pip

# Expected output: Successfully installed pip X.Y.Z
```

### Step 4: Install Dependencies

```powershell
# Install all required packages
pip install -r requirements.txt

# This will download models (~1GB)
# Time estimate: 5-15 minutes depending on internet speed
```

**Expected Dependencies Installed**:

- torch (2.0.1+)
- torchvision (0.15.2+)
- transformers (4.31.0+)
- ultralytics (8.0.124+) - YOLOv8
- opencv-python-headless (4.8.0+)
- easyocr (1.7.0+)
- speechrecognition (3.10.0+)
- pyttsx3 (2.90+)
- gTTS (2.3.2+)
- sqlalchemy (2.0.19+)
- openai (1.0.0+)

### Step 5: Configure Environment Variables

```powershell
# Copy environment template
copy .env.example .env

# Edit .env in text editor (Notepad, VSCode, etc.)
notepad .env
```

**Add your API keys**:

```ini
OPENAI_API_KEY=sk-your-key-here
SPEECH_LANGUAGE=en
DEVICE=cpu
```

### Step 6: Verify Installation

```powershell
# Test imports
python -c "import torch, cv2, transformers; print('✓ Core packages OK')"

# Test application
python -c "from app import VisionAssistant; print('✓ Application imported')"

# Test database
python -c "from database.db_handler import DatabaseHandler; print('✓ Database OK')"
```

### Step 7: Run Application

```powershell
# Start Vision Assistant
python app.py

# Expected output:
# Vision Assistant initialized
# Listening for voice commands...
```

---

## macOS Installation

### Step 1: Install Python (if needed)

**Option A: Homebrew (Recommended)**

```bash
# Install Homebrew if not already installed
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python
brew install python@3.11

# Verify
python3 --version
```

**Option B: Direct Download**

1. Visit [python.org](https://www.python.org/downloads/macos/)
2. Download Python 3.11 or later
3. Run installer
4. Follow installation wizard

### Step 2: Install System Dependencies

```bash
# Audio libraries
brew install portaudio

# Build tools
xcode-select --install

# Other optional packages
brew install openssl
```

### Step 3: Create Virtual Environment

```bash
# Navigate to project directory
cd aiforus

# Create virtual environment
python3 -m venv venv

# Activate
source venv/bin/activate

# Expected: (venv) prefix in terminal
```

### Step 4: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 5: Install Dependencies

```bash
# Install all packages
pip install -r requirements.txt

# Time estimate: 5-15 minutes
```

**For Apple Silicon (M1/M2) Macs**:

```bash
# If you encounter issues, use native architecture
ARCHFLAGS=-Wno-error=unused-command-line-argument-hard-error-in-future pip install -r requirements.txt

# Or use conda (alternative)
conda create -n visionai python=3.11
conda activate visionai
conda install pytorch torchvision torchaudio -c pytorch
pip install -r requirements.txt
```

### Step 6: Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit with your preferred editor
nano .env
# or
open -a "Visual Studio Code" .env
```

### Step 7: Verify Installation

```bash
# Test imports
python -c "import torch, cv2, transformers; print('✓ Core packages OK')"

# Test application
python -c "from app import VisionAssistant; print('✓ Application imported')"

# Test audio
python -c "import pyttsx3; engine = pyttsx3.init(); print('✓ TTS OK')"
```

### Step 8: Grant Microphone Permission

For first-time use:

1. Open System Preferences
2. Go to Security & Privacy → Microphone
3. Add Terminal or Python to the allowed apps list
4. Or run application and grant permission when prompted

### Step 9: Run Application

```bash
python app.py

# Expected output:
# Vision Assistant initialized
# Listening for voice commands...
```

---

## Linux Installation

### Step 1: Install Python

**Ubuntu/Debian**:

```bash
# Update package lists
sudo apt-get update

# Install Python and pip
sudo apt-get install python3.11 python3.11-venv python3.11-dev -y

# Set as default (optional)
sudo update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1

# Verify
python --version
```

**CentOS/RHEL**:

```bash
sudo yum install python3.11 python3.11-devel -y
python3.11 --version
```

**Fedora**:

```bash
sudo dnf install python3.11 python3.11-devel -y
python3.11 --version
```

### Step 2: Install System Dependencies

**Ubuntu/Debian**:

```bash
# Essential build tools
sudo apt-get install build-essential git -y

# Audio libraries
sudo apt-get install portaudio19-dev libsndfile1 -y

# Computer vision libraries
sudo apt-get install libgl1-mesa-glx libgomp1 -y

# Speech recognition (optional)
sudo apt-get install alsa-utils -y
```

**CentOS/RHEL**:

```bash
# Build tools
sudo yum groupinstall "Development Tools" -y

# Audio libraries
sudo yum install portaudio-devel -y

# Graphics libraries
sudo yum install mesa-libGL -y
```

**Fedora**:

```bash
# Build tools
sudo dnf groupinstall "Development Tools" -y

# Audio libraries
sudo dnf install portaudio-devel -y

# Graphics libraries
sudo dnf install mesa-libGL -y
```

### Step 3: Configure Audio (if needed)

```bash
# Check if user is in audio group
groups $USER

# Add user to audio group (requires logout/login)
sudo usermod -a -G audio $USER

# Apply group immediately
newgrp audio

# Verify
groups $USER  # Should now include 'audio'
```

### Step 4: Configure Camera (if using)

```bash
# Check if user is in video group
groups $USER

# Add user to video group
sudo usermod -a -G video $USER

# Apply immediately
newgrp video

# List camera devices
v4l2-ctl --list-devices
```

### Step 5: Create Virtual Environment

```bash
# Navigate to project
cd aiforus

# Create virtual environment
python -m venv venv

# Activate
source venv/bin/activate

# Expected: (venv) prefix in terminal
```

### Step 6: Upgrade pip

```bash
python -m pip install --upgrade pip
```

### Step 7: Install Dependencies

```bash
pip install -r requirements.txt

# Time estimate: 5-15 minutes
```

**Troubleshooting Common Issues**:

If you encounter PyAudio errors:

```bash
pip install --no-cache-dir pyaudio
```

If you encounter OpenCV errors:

```bash
pip install opencv-python-headless
```

If CUDA out of memory occurs:

```bash
# Edit config.yaml and set device to cpu
# Or install CPU-only PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

### Step 8: Configure Environment

```bash
# Copy template
cp .env.example .env

# Edit with nano or your editor
nano .env
```

**Minimum Configuration**:

```ini
OPENAI_API_KEY=sk-your-key-here
DEVICE=cpu
SPEECH_LANGUAGE=en
```

### Step 9: Verify Installation

```bash
# Test imports
python -c "import torch, cv2, transformers; print('✓ Core packages OK')"

# Check camera
python -c "
import cv2
cap = cv2.VideoCapture(0)
status = cap.isOpened()
cap.release()
print(f'Camera: {\"✓ OK\" if status else \"✗ Not available (optional)\"}')
"

# Test microphone
python -c "
import speech_recognition as sr
r = sr.Recognizer()
with sr.Microphone() as source:
    print('✓ Microphone accessible')
"

# Test application
python -c "from app import VisionAssistant; print('✓ Application ready')"
```

### Step 10: Run Application

```bash
python app.py

# Expected output:
# Vision Assistant initialized
# Listening for voice commands...
```

---

## Post-Installation Verification

### Comprehensive Check

Run this verification script:

```bash
# Activate virtual environment first
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate     # Windows

# Run verification
python -c "
import sys
import torch
import cv2
import transformers
from ultralytics import YOLO
import easyocr
import speech_recognition
import pyttsx3
from gtts import gTTS
import sqlalchemy
from openai import OpenAI

print('✓ Python version:', sys.version.split()[0])
print('✓ PyTorch:', torch.__version__)
print('✓ OpenCV:', cv2.__version__)
print('✓ Transformers:', transformers.__version__)
print('✓ YOLOv8 available')
print('✓ EasyOCR available')
print('✓ Speech Recognition:', speech_recognition.__version__)
print('✓ pyttsx3:', pyttsx3.__version__)
print('✓ gTTS available')
print('✓ SQLAlchemy:', sqlalchemy.__version__)
print('✓ OpenAI available')
print('✓ All dependencies installed successfully!')
"
```

### First Run

```bash
# Activate virtual environment
source venv/bin/activate

# Run application
python app.py

# You should hear: "Vision Assistant initialized"
# Ready for commands: "What do you see?"
```

---

## Configuration

### Environment Variables

Create or edit `.env` file:

```ini
# API Keys (required for full features)
OPENAI_API_KEY=sk-your-openai-key-here
GOOGLE_MAPS_API_KEY=your-google-maps-key-here

# Application Settings
DEVICE=cpu                    # 'cpu' or 'cuda'
SPEECH_LANGUAGE=en           # Language code
DEBUG=false                   # Debug mode

# Database
DATABASE_URL=sqlite:///vision_assistant.db
```

### Configuration File

Edit `config.yaml`:

```yaml
app:
  name: Vision Assistant
  debug: false
  version: "1.0.0"

ai:
  llm_provider: openai # 'openai' or 'local'
  vision_model: yolov8n # 'yolov8n', 'yolov8s', 'yolov8m', etc.
  text_model: easyocr # Text recognition model
  device: cpu # 'cpu' or 'cuda'

speech:
  language: en # Language code
  speech_rate: 150 # Words per minute (50-300)
  use_google_tts: false # Use online TTS

accessibility:
  voice_feedback: true # Enable voice responses
  audio_cues: true # Enable audio notifications

vision:
  camera_index: 0 # Camera device index
  detection_confidence: 0.5 # Object detection threshold

database:
  path: vision_assistant.db # SQLite database file
```

---

## Quick Start

After successful installation:

```bash
# 1. Activate environment
source venv/bin/activate      # macOS/Linux
# or
venv\Scripts\activate         # Windows

# 2. Run application
python app.py

# 3. Try a command (speak to microphone):
# "What do you see?"
# "Read the text"
# "What objects are here?"
# "Goodbye" (to exit)
```

---

## Troubleshooting Installation

### Common Issues and Solutions

#### Python Not Found

```bash
# Use python3 instead
python3 --version

# Or add Python to PATH
# Windows: Settings → Environment Variables → PATH → Add Python directory
# macOS/Linux: Already in PATH after installation
```

#### Permission Denied (Linux/macOS)

```bash
# Add execute permission
chmod +x venv/bin/activate
```

#### ModuleNotFoundError

```bash
# Verify virtual environment is active
# Should show (venv) prefix in terminal

# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

#### Timeout During Installation

```bash
# Increase timeout
pip install --default-timeout 100 -r requirements.txt

# Or install packages individually
pip install torch torchvision transformers ultralytics
pip install opencv-python-headless easyocr
```

#### GPU Not Detected

```bash
# Check if CUDA is available
python -c "import torch; print(torch.cuda.is_available())"

# If False, install CPU version (application will use CPU automatically)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
```

#### ImportError on Linux

```bash
# Install missing libraries
sudo apt-get install libgl1-mesa-glx   # For OpenGL
sudo apt-get install portaudio19-dev   # For audio
```

#### Microphone Not Working

**Windows**: Open Volume Mixer and select default microphone

**macOS/Linux**: Check permissions

```bash
# macOS: System Preferences → Security & Privacy → Microphone
# Linux: Check if in audio group
groups $USER
```

#### Camera Not Accessible

```bash
# Linux: Add to video group
sudo usermod -a -G video $USER
newgrp video

# Verify camera
v4l2-ctl --list-devices
```

---

## Advanced Setup

### GPU Acceleration (CUDA)

For NVIDIA GPUs:

```bash
# Install CUDA-capable PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify
python -c "import torch; print('GPU:', torch.cuda.is_available())"

# Update config.yaml
# ai:
#   device: cuda
```

### Docker Installation

```bash
# Build Docker image
docker build -t vision-assistant:1.0 .

# Run container
docker run -d \
  --name vision-assistant \
  -v $(pwd)/config.yaml:/app/config.yaml \
  vision-assistant:1.0

# View logs
docker logs -f vision-assistant
```

### Conda Installation

```bash
# Create conda environment
conda create -n visionai python=3.11
conda activate visionai

# Install PyTorch via conda
conda install pytorch torchvision torchaudio pytorch::cuda-toolkit -c pytorch -c conda-forge

# Install other dependencies
pip install -r requirements.txt
```

---

## Uninstallation

### Remove Virtual Environment

```bash
# Windows
rmdir /s venv

# macOS/Linux
rm -rf venv
```

### Remove Database

```bash
# Windows
del database\vision_assistant.db

# macOS/Linux
rm database/vision_assistant.db
```

### Clean Cache

```bash
# Remove Python cache
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete

# Remove model cache (if desired)
# Models stored in ~/.cache/torch, ~/.cache/huggingface, etc.
```

---

## Next Steps

1. ✅ Installation complete
2. 📖 Read [README.md](/README.md) for project overview
3. 🚀 Try [QUICKREF.md](../QUICKREF.md) for voice commands
4. 🔧 See [ARCHITECTURE.md](../ARCHITECTURE.md) to understand the system
5. 🐛 Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) if issues occur

---

## Getting Help

### Documentation

- [README.md](/README.md) - Project overview
- [QUICKREF.md](../QUICKREF.md) - Quick reference
- [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) - Common issues
- [INDEX.md](../INDEX.md) - Documentation index

### Support

- Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md) first
- Review [GitHub Issues](https://github.com/Khaf-dev/aiforus/issues)
- See [CONTRIBUTING.md](../guidelines/CONTRIBUTING.md) to report issues

---

## System Dependencies Summary

### Required

- Python 3.8+
- pip
- Build tools (gcc, make, etc.)

### Recommended

- Git (for version control)
- Virtual environment support
- OpenSSL/TLS libraries

### Optional

- NVIDIA CUDA Toolkit (for GPU acceleration)
- Docker (for containerization)
- Conda (alternative Python environment)

---

**Installation Version**: 1.0.0  
**Last Updated**: 2024-12-20  
**Status**: ✅ Production Ready

See [INDEX.md](../INDEX.md) for complete documentation navigation.
