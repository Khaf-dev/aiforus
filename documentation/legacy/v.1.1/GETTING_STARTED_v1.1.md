# Getting Started with Vision Assistant v1.1

A practical guide to getting started with the new features in Vision Assistant v1.1.

---

## Prerequisites

- Python 3.8 or higher
- Virtual environment activated
- All dependencies installed
- Microphone and/or camera (optional for basic features)

### Quick Setup Check

```bash
# Verify Python version
python --version  # Should be 3.8+

# Check virtual environment
which python  # Should show venv path

# Test core imports
python -c "import torch, cv2, transformers, sqlalchemy; print('✓ Ready')"
```

---

## Getting Started: Multi-Language Support

### 1. Basic Usage

Start the assistant:

```bash
python app.py --lang=es
# Starts in Spanish

python app.py  # Starts in English (default)
```

### 2. Switch Languages via Voice

Once running:

```
User: "Switch to Spanish"
🎙️ Assistant: "Idioma cambiado a español"

User: "Change language to Indonesian"
🎙️ Assistant: "Bahasa diubah ke Indonesia"
```

### 3. View Available Languages

```bash
python -c "
from ai_modules.speech_engine import SpeechEngine
speech = SpeechEngine()
languages = speech.get_available_languages()
for code, name in languages.items():
    print(f'{code}: {name}')
"
```

### 4. Configuration

Set default language in `config.yaml`:

```yaml
speech:
  language: "en" # Change to es, id, fr, de, pt, ja, zh
  speech_rate: 150
```

### 5. Voice Commands by Language

**English:**

```
"What do you see?"
"Describe this"
"Switch to Spanish"
"Go to the kitchen"
```

**Spanish:**

```
"¿Qué ves?" (What do you see?)
"Describe esto" (Describe this)
"Cambiar a inglés" (Switch to English)
```

**Indonesian:**

```
"Apa yang kamu lihat?" (What do you see?)
"Jelaskan ini" (Describe this)
"Ubah ke bahasa Indonesia" (Switch to Indonesian)
```

---

## Getting Started: Face Recognition

### 1. Enable Face Recognition

In `config.yaml`:

```yaml
face_recognition:
  enabled: true
  mode: "recognition"
  detection_confidence: 0.6
```

### 2. Enroll Your First Person

Start assistant:

```bash
python app.py
```

Voice command:

```
User: "Enroll new person"
🎙️ Assistant: "What is their name?"
User: "John"
🎙️ Assistant: "Please look at the camera for enrollment"
[Camera captures 5 samples]
🎙️ Assistant: "John has been enrolled successfully"
```

### 3. Test Recognition

```
User: "Who is in front of me?"
🎙️ Assistant: "I see John at 95% confidence"
```

### 4. Manage Enrolled People

**List all people:**

```
User: "Who do you know?"
🎙️ Assistant: "I know John, Sarah, and Mom"
```

**Remove person:**

```
User: "Forget John"
🎙️ Assistant: "John has been removed"
```

**Get statistics:**

```
User: "How many people do you know?"
🎙️ Assistant: "I have enrolled 3 people with 15 face samples"
```

### 5. Manual Enrollment (Scripting)

```python
from app import VisionAssistant

async def enroll_people():
    assistant = VisionAssistant()

    # Enroll person
    success = await assistant.face_recognizer.enroll_face('Mom', num_samples=5)

    if success:
        print("Mom enrolled successfully")

    # List all
    people = assistant.face_recognizer.get_known_people()
    print(f"Enrolled people: {people}")

# Run
import asyncio
asyncio.run(enroll_people())
```

### 6. Troubleshooting Face Recognition

**Issue: "No face detected"**

- Ensure good lighting (>500 lux)
- Position face 30-50cm from camera
- Face should be centered and clear

**Issue: "Low confidence"**

- Re-enroll with different angles
- Use `training_samples: 10` in config
- Ensure consistent lighting

**Issue: "Camera permission denied"**

- Linux: `sudo usermod -a -G video $USER`
- Windows: Run as administrator
- macOS: Grant camera permission in System Preferences

---

## Getting Started: Sound Localization

### 1. Enable Sound Localization

In `config.yaml`:

```yaml
sound_localization:
  enabled: true
  mode: "localization"
  obstacles:
    enabled: true
```

### 2. Test Sound Detection

Start assistant:

```bash
python app.py
```

Voice command:

```
User: "What sounds do you hear?"
🎙️ Assistant: "I hear traffic ahead at 45 degrees, 8 meters away"
```

### 3. Listen for Obstacles

```
User: "Guide me forward"
🎙️ Assistant: "Path clear... wall detected 2 meters to your right"
```

### 4. Sound Classification

The system identifies:

- **Speech** - Voices and conversations
- **Vehicles** - Cars, trucks, motorcycles
- **Alarms** - Sirens, bells, alerts
- **Noise** - General environmental noise

### 5. 8-Direction Compass

Sounds are localized to:

```
        Front (0°)
             |
Left ←  ·  ·  ·  → Right
        |
       Back (180°)
```

Example responses:

```
"Sound to your right front, 5 meters"
"Vehicle alarm back-left, 3 meters"
"Clear forward, traffic on left side"
```

### 6. Obstacle Detection Levels

```
0.5 - 2.0 meters: Red zone (immediate danger)
2.0 - 5.0 meters: Yellow zone (caution)
5.0+ meters: Green zone (clear)
```

Responses:

```
Red:    "Wall 1 meter to your right!"
Yellow: "Caution, obstacle 3 meters ahead"
Green:  "Clear ahead for 5 meters"
```

### 7. Manual Testing (Scripting)

```python
from ai_modules.sound_localization import SoundLocalizer

async def test_localization():
    localizer = SoundLocalizer()

    # Start listening
    if localizer.start_listening():

        # Detect sounds
        sounds = await localizer.detect_sounds()
        if sounds:
            print("Detected sounds:", sounds)

        # Get description
        description = localizer.get_audio_description()
        print(description)

        # Stop
        localizer.stop_listening()

import asyncio
asyncio.run(test_localization())
```

### 8. Troubleshooting Sound Localization

**Issue: "No sounds detected"**

- Check microphone permissions
- Test with loud sound nearby
- Increase `sound_sensitivity` in config

**Issue: "Inaccurate direction"**

- Single microphone has limited accuracy
- Use stereo microphone array for better results
- Ensure quiet environment for testing

**Issue: "PyAudio ImportError"**

- Install: `pip install pyaudio`
- Linux: `sudo apt-get install portaudio19-dev`
- macOS: `brew install portaudio`

---

## Combining Features

### Complete Scenario: Navigate to a Cafe

```
User: "Find a cafe and guide me there"

1️⃣ Location Detection
   Assistant: "You are at Main Street intersection"

2️⃣ Find Nearby
   Assistant: "Coffee Corner cafe is 200 meters north"

3️⃣ Get Directions
   Assistant: "Turn right, walk 50 meters straight"

4️⃣ Obstacle Awareness
   [Audio detects car]
   Assistant: "Car approaching from left, wait"

5️⃣ Face Recognition
   [Person enters view]
   Assistant: "Hello John! Following you?"

6️⃣ Language Support
   User: "Switch to Spanish"
   Assistant: "Café Corner está a 200 metros"

7️⃣ Obstacle Detection
   Assistant: "Wall 2 meters right, cafe entrance 100 meters ahead"

8️⃣ Arrival
   Assistant: "We have arrived at Coffee Corner"
```

---

## Common Voice Commands v1.1

### Multi-Language

```
"Switch to Spanish"
"Change language to Indonesian"
"What languages do you support?"
```

### Face Recognition

```
"Enroll new person"
"Who is in front of me?"
"Who do you know?"
"Forget John"
"Face statistics"
```

### Sound Localization

```
"What sounds do you hear?"
"Describe the audio scene"
"Detect obstacles"
"Guide me forward"
"Any danger ahead?"
```

### Navigation

```
"Navigate to nearest hospital"
"What's close by?"
"How far is the station?"
"Give me directions"
```

### Vision

```
"What do you see?"
"Describe my surroundings"
"Read the sign"
"Detect objects"
```

---

## Configuration Quick Reference

### Essential Settings

```yaml
# Default language
speech:
  language: "en" # en, es, id, fr, de, pt, ja, zh

# Face recognition accuracy
face_recognition:
  detection_confidence: 0.6 # 0.0-1.0
  recognition_confidence: 0.6
  max_people: 20 # Maximum enrolled people

# Audio sensitivity
sound_localization:
  sound_sensitivity: 0.5 # 0.0-1.0 (higher = more sensitive)
  noise_threshold: -40 # dB (lower = detects quieter sounds)
```

### Performance Tuning

```yaml
# For slow devices
vision:
  detection_confidence: 0.7  # Higher = faster, less accurate

# For noisy environments
sound_localization:
  noise_threshold: -30  # Higher = ignores quiet noise

# For low light
vision:
  sensitivity: 1.5  # Higher = detection in low light
```

---

## Testing Your Setup

### Test Audio Input

```bash
python -c "
import pyaudio
p = pyaudio.PyAudio()
print(f'Devices: {p.get_device_count()}')
for i in range(p.get_device_count()):
    info = p.get_device_info_by_index(i)
    if 'input' in info['name'].lower():
        print(f'{i}: {info[\"name\"]}')
"
```

### Test Camera

```bash
python -c "
import cv2
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
if ret:
    print('✓ Camera working')
else:
    print('✗ Camera failed')
cap.release()
"
```

### Test All Features

```bash
# Import test
python -c "
from app import VisionAssistant
from ai_modules.sound_localization import SoundLocalizer
from features.face_recognition import FaceRecognizer
print('✓ All imports successful')
"

# Config test
python -c "
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
assert 'sound_localization' in config
print('✓ Config valid')
"
```

---

## Performance Tips

### Speed Optimization

1. Lower detection confidence threshold
2. Use smaller models (if available)
3. Reduce face training samples to 3
4. Disable features you don't use

### Accuracy Optimization

1. Increase training samples to 10
2. Enroll faces in different lighting
3. Use stereo microphones for audio
4. Reduce noise threshold for sensitivity

### Memory Optimization

```yaml
# Reduce buffering
sound_localization:
  chunk_size: 512 # Lower = less memory

# Limit enrolled people
face_recognition:
  max_people: 10 # Lower = less memory
```

---

## Next Steps

1. **Install All Features:** Follow the setup for each phase
2. **Test Voice Commands:** Practice speaking clearly
3. **Enroll Faces:** Create your personal AI assistant
4. **Configure Settings:** Tune for your environment
5. **Read Full Docs:** See [FEATURES_v1.1.md](FEATURES_v1.1.md)
6. **Explore API:** Check [API_REFERENCE.md](../guidelines/API_REFERENCE.md)

---

## Need Help?

- **Issues:** Check [TROUBLESHOOTING.md](../TROUBLESHOOTING.md)
- **API Details:** See [API_REFERENCE.md](../guidelines/API_REFERENCE.md)
- **Features Guide:** Read [FEATURES_v1.1.md](FEATURES_v1.1.md)
- **Contributing:** See [CONTRIBUTING.md](../guidelines/CONTRIBUTING.md)

---

**Ready to experience the future of accessibility!** 🎙️👤🔊
