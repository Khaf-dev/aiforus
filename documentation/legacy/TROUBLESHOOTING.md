# Troubleshooting Guide

This guide helps resolve common issues when running Vision Assistant.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Runtime Errors](#runtime-errors)
3. [Audio Problems](#audio-problems)
4. [Camera Issues](#camera-issues)
5. [Performance Issues](#performance-issues)
6. [Database Problems](#database-problems)
7. [API Errors](#api-errors)
8. [Platform-Specific Issues](#platform-specific-issues)

---

## Installation Issues

### ModuleNotFoundError: No module named 'X'

**Symptom**: `ModuleNotFoundError: No module named 'torch'` (or other package)

**Solutions**:

```bash
# 1. Verify virtual environment is active
python --version  # Should show venv path

# 2. Reinstall dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 3. For stubborn packages, reinstall specifically
pip install --force-reinstall torch

# 4. Check pip cache issues
pip install --no-cache-dir -r requirements.txt
```

**Common Packages to Check**:

- torch
- torchvision
- transformers
- ultralytics
- opencv-python-headless

---

### Package Installation Timeout

**Symptom**: `ReadTimeoutError` when installing packages

**Cause**: Network timeout, slow PyPI mirror, or slow internet

**Solutions**:

```bash
# Increase timeout (default 15 seconds)
pip install --default-timeout 100 -r requirements.txt

# Use faster PyPI mirror
pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/

# Or use official PyPI (default)
pip config set global.index-url https://pypi.org/simple/

# Try installing packages one by one
pip install torch torchvision transformers ultralytics
```

---

### GPU/CUDA Issues

**Symptom**: PyTorch uses CPU instead of GPU

**Verify GPU Support**:

```python
import torch
print(torch.cuda.is_available())  # Should print True if GPU available
print(torch.cuda.get_device_name(0))  # Shows GPU name
```

**Solutions**:

```bash
# Install CUDA-compatible PyTorch
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify installation
python -c "import torch; print(f'GPU: {torch.cuda.is_available()}')"
```

**If Still CPU Only**:

- GPU drivers may not be installed
- CUDA toolkit not installed
- Application defaults to CPU (this is acceptable)

---

## Runtime Errors

### AttributeError: 'SpeechEngine' object has no attribute 'speech_rate'

**Symptom**: Error during initialization

**Cause**: Initialization order issue (usually already fixed)

**Solution**:

```bash
# Delete old database to force fresh initialization
rm database/vision_assistant.db

# Reinstall application
pip install -r requirements.txt

# Run again
python app.py
```

---

### TypeError: 'coroutine' object is not awaitable

**Symptom**: Error about awaiting non-async function

**Cause**: Missing `await` or `async` keyword

**Example of Wrong Code**:

```python
# Wrong
result = assistant.listen()  # Should be await

# Correct
result = await assistant.listen()
```

**Solution**: Ensure all calls to async functions use `await`

---

### FileNotFoundError: config.yaml not found

**Symptom**: `FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'`

**Solution**:

```bash
# Verify you're in the correct directory
pwd  # Should show d:\aiforus or similar

# Check if file exists
ls config.yaml

# If missing, create the file
# See INSTALLATION.md for template
```

---

## Audio Problems

### Microphone Not Detected

**Symptom**: Application hangs on `listen()`, or "No microphone input"

**Debug Steps**:

```bash
# Test microphone access
python -c "
import speech_recognition as sr
recognizer = sr.Recognizer()
with sr.Microphone() as source:
    print('Microphone accessible')
"
```

**Solutions**:

**Windows**:

```bash
# Use Volume Mixer to select default microphone
# Settings → Sound → Advanced → App volume and device preferences
```

**Linux**:

```bash
# Check audio permissions
groups $USER  # Should include 'audio' group

# Add user to audio group (requires logout/login)
sudo usermod -a -G audio $USER

# Install audio libraries
sudo apt-get install portaudio19-dev python3-pyaudio

# Reinstall pyaudio
pip install --force-reinstall pyaudio
```

**macOS**:

```bash
# Grant microphone permission to Terminal/Python
# System Preferences → Security & Privacy → Microphone
```

---

### Speaker/Output Not Working

**Symptom**: Application doesn't produce sound, or TTS fails silently

**Debug Steps**:

```bash
# Test TTS directly
python -c "
from ai_modules.speech_engine import SpeechEngine
se = SpeechEngine()
se.speak('Hello world')
"
```

**Solutions**:

**pyttsx3 Issues**:

```bash
# Reinstall with specific backend
pip install --force-reinstall pyttsx3

# Test with gTTS instead
python -c "
from gtts import gTTS
tts = gTTS('Hello', lang='en')
tts.save('test.mp3')
"
```

**ALSA Warnings** (harmless on Linux):

```bash
# These can be safely ignored:
# ALSA lib pcm.c:... Unknown PCM cards
# ALSA lib confmisc.c:... etc.

# To suppress warnings:
python -c "
import warnings
# Continue with imports
"
```

**No Sound from Speaker**:

```bash
# Check volume settings
# Windows: Volume Mixer → Adjust app volume
# Linux: alsamixer or pavucontrol
# macOS: System Preferences → Sound → Output
```

---

### Permission Denied: /dev/dsp or /dev/snd

**Symptom**: `PermissionError` when accessing audio device

**Cause**: User not in audio group

**Solution**:

```bash
# Add user to audio group
sudo usermod -a -G audio $USER

# Apply group change (requires logout and login)
# Or use:
sudo su - $USER

# Verify
groups $USER  # Should now include 'audio'
```

---

## Camera Issues

### Camera Not Detected

**Symptom**: OpenCV returns `None` or empty image

**Debug Steps**:

```bash
# Test camera directly
python -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
print(f'Camera available: {ret}')
cap.release()
"
```

**Solutions**:

**Windows**:

- Check Device Manager → Imaging devices
- Ensure camera driver is installed
- Some laptops require BIOS setting to enable camera

**Linux**:

```bash
# Check camera permissions
ls -la /dev/video*

# Add user to video group
sudo usermod -a -G video $USER

# Install camera utilities
sudo apt-get install v4l-utils
v4l2-ctl --list-devices
```

**macOS**:

- Grant camera permission to Terminal/Python
- System Preferences → Security & Privacy → Camera

---

### Camera Feed Freezes or Lags

**Symptom**: Video capture is slow, image quality poor, or camera hangs

**Cause**: Camera sharing with other applications, low light, or hardware issue

**Solutions**:

```bash
# Close other camera apps (Zoom, Teams, etc.)

# Adjust resolution and FPS in config.yaml
# Lower resolution = faster processing
camera_width: 320  # instead of 1280
camera_height: 240  # instead of 960

# Try different camera index
python -c "
import cv2
for i in range(5):
    cap = cv2.VideoCapture(i)
    if cap.isOpened():
        print(f'Camera {i} available')
    cap.release()
"
```

---

## Performance Issues

### Application Startup Takes Too Long

**Symptom**: Application takes >10 seconds to start

**Cause**: Models downloading, GPU initialization, or hardware constraints

**Solutions**:

```bash
# 1. Models download on first run (~1GB total)
# This is normal the first time. Subsequent runs are faster.

# 2. Check system resources
# Use Task Manager (Windows) or top (Linux/macOS)

# 3. Use smaller models
# Edit config.yaml:
ai:
  vision_model: yolov8n  # nano (fastest)
  # other options: yolov8s, yolov8m, yolov8l, yolov8x

# 4. Preload models on login
# Run at system startup to cache models
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

---

### Object Detection is Slow (<2 FPS)

**Symptom**: Object detection takes 500ms+ per image

**Cause**: CPU processing, large models, or low-spec hardware

**Solutions**:

```bash
# 1. Use GPU if available
# Edit config.yaml:
ai:
  device: cuda  # uses GPU automatically

# 2. Use nano/small models
ai:
  vision_model: yolov8n

# 3. Lower resolution
camera_width: 320
camera_height: 240

# 4. Skip unnecessary detections
# Modify frequency of vision processing in app.py
```

**Acceptable Performance**:

- CPU (i5/i7): 100-200ms per image
- CPU (low-end): 300-500ms per image
- GPU (GTX 1060): 50-100ms per image
- GPU (RTX 3060+): 20-50ms per image

---

### Memory Usage Constantly Increasing

**Symptom**: RAM usage grows from 500MB to 1GB+ over time

**Cause**: Memory leak in model processing or database queries

**Solutions**:

```bash
# 1. Restart application periodically
# Set a daily restart in cron:
crontab -e
# Add: 0 3 * * * /path/to/restart_vision_assistant.sh

# 2. Clear database history
python -c "
from database.db_handler import DatabaseHandler
db = DatabaseHandler()
db.cleanup_old_sessions()
"

# 3. Profile memory usage
python -m memory_profiler app.py
```

---

## Database Problems

### sqlite3.OperationalError: database is locked

**Symptom**: Database access error, multiple processes accessing DB

**Cause**: Multiple app instances running or improper shutdown

**Solutions**:

```bash
# 1. Kill existing process
# Windows:
taskkill /IM python.exe /F

# Linux/macOS:
pkill -f "python app.py"

# 2. Check for lock file
ls -la database/

# 3. Delete lock file if present
rm database/vision_assistant.db-journal

# 4. Restart application
python app.py
```

---

### Unknown column 'disability_type'

**Symptom**: `OperationalError: no such column: users.disability_type`

**Cause**: Database schema outdated (usually already fixed)

**Solution**:

```bash
# Delete old database to recreate with new schema
rm database/vision_assistant.db

# Application will recreate on next run
python app.py
```

---

### Unable to Create Database File

**Symptom**: `PermissionError` when creating vision_assistant.db

**Cause**: No write permission to database directory

**Solution**:

```bash
# Check permissions
ls -la database/

# Fix permissions
chmod 755 database/
chmod 644 database/vision_assistant.db

# Verify
python -c "
from database.db_handler import DatabaseHandler
db = DatabaseHandler()
print('Database OK')
"
```

---

## API Errors

### OpenAI API Error: Invalid API Key

**Symptom**: `openai.error.AuthenticationError: Invalid API key`

**Cause**: Missing or incorrect API key

**Solution**:

```bash
# 1. Create .env file (copy from .env.example)
cp .env.example .env

# 2. Edit .env with your OpenAI API key
# OPENAI_API_KEY=sk-...

# 3. Verify API key works
python -c "
import os
from openai import OpenAI
client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
print('API key valid')
"

# 4. Restart application
python app.py
```

**Get API Key**:

- Visit [openai.com/api/](https://platform.openai.com/api-keys)
- Create new secret key
- Copy to .env file

---

### OpenAI API Error: Rate Limit

**Symptom**: `RateLimitError: Too many requests`

**Cause**: Exceeded API quota or rate limit

**Solution**:

```bash
# 1. Reduce API calls in config.yaml
ai:
  llm_provider: local  # Use local intent matching instead

# 2. Add request throttling
# Edit llm_handler.py to add delays between requests

# 3. Remove OPENAI_API_KEY to use local only
# Edit .env or app.py
```

---

### Network Error: Cannot reach API

**Symptom**: `ConnectionError` when calling external APIs

**Cause**: No internet connection or service unreachable

**Solution**:

```bash
# 1. Check internet connection
ping 8.8.8.8  # Google DNS

# 2. Verify service status
# OpenAI: https://status.openai.com
# Google: https://www.google.com/appsstatus

# 3. Use local-only mode
# Edit config.yaml:
ai:
  llm_provider: local
```

---

## Platform-Specific Issues

### Windows: Python not found

**Symptom**: `'python' is not recognized as an internal or external command`

**Solution**:

```bash
# Use python3 instead
python3 app.py

# Or add Python to PATH
# Windows Settings → Environment Variables → PATH → Add Python directory
```

---

### Linux: libGL.so.1 not found

**Symptom**: `libGL.so.1: cannot open shared object file`

**Cause**: OpenGL library not installed

**Solution**:

```bash
# Ubuntu/Debian
sudo apt-get install libgl1-mesa-glx

# CentOS/RHEL
sudo yum install mesa-libGL

# Fedora
sudo dnf install mesa-libGL
```

---

### macOS: Module not found (M1/M2 chip)

**Symptom**: Module import fails on Apple Silicon

**Cause**: Architecture mismatch (Intel vs ARM)

**Solution**:

```bash
# Create new virtual environment for ARM
python3 -m venv venv_arm

# Install PyTorch for ARM
pip install torch::nightly --pre --index-url https://download.pytorch.org/whl/nightly/cpu

# Or use miniforge
# https://github.com/conda-forge/miniforge
```

---

### WSL (Windows Subsystem for Linux): Audio not working

**Symptom**: No sound output in WSL

**Cause**: WSL audio redirection requires additional setup

**Solution**:

```bash
# 1. Update WSL2
wsl --update

# 2. Use Windows audio device from WSL
# Set PulseAudio to Windows host

# 3. Or use text-only mode
# Set config.yaml:
speech:
  use_google_tts: false
```

---

## Getting More Help

### Debug Mode

```bash
# Run with verbose logging
python app.py --debug

# Or set environment variable
DEBUG=true python app.py
```

### Collect System Information

```bash
python -c "
import platform
import sys
print(f'Python: {sys.version}')
print(f'Platform: {platform.platform()}')
print(f'Architecture: {platform.machine()}')

import torch
print(f'PyTorch: {torch.__version__}')
print(f'CUDA: {torch.version.cuda}')
print(f'GPU: {torch.cuda.is_available()}')
"
```

### Check Application Logs

```bash
# View recent logs
tail -50 vision_assistant.log

# Or on Windows
type vision_assistant.log | More
```

---

## Still Having Issues?

1. **Check** [INSTALLATION.md](INSTALLATION.md) for setup steps
2. **Review** [API.md](API.md) for usage examples
3. **Read** [ARCHITECTURE.md](ARCHITECTURE.md) for design context
4. **Open** GitHub issue with:
   - Error message (with stack trace)
   - System information (OS, Python version)
   - Steps to reproduce
   - Expected vs actual behavior

---

## See Also

- [INSTALLATION.md](./setup/INSTALLATION.md) - Setup guide
- [README.md](../README.md) - Project overview
- [CONTRIBUTING.md](./guidelines/CONTRIBUTING.md) - How to contribute
