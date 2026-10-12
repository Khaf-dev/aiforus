# Configuration Guide - Vision Assistant v1.1

Complete reference for all configuration options in Vision Assistant v1.1.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Speech Configuration](#speech-configuration)
3. [Face Recognition Configuration](#face-recognition-configuration)
4. [Sound Localization Configuration](#sound-localization-configuration)
5. [Vision Configuration](#vision-configuration)
6. [Navigation Configuration](#navigation-configuration)
7. [Environment Variables](#environment-variables)
8. [Example Configurations](#example-configurations)

---

## Quick Start

Edit `config.yaml` in the project root:

```bash
# Copy example config (if not present)
cp config.yaml config.yaml.backup

# Edit with your favorite editor
nano config.yaml  # Linux/macOS
code config.yaml  # VS Code
```

Restart the application to apply changes:

```bash
python app.py
```

---

## Speech Configuration

### Default Language

```yaml
speech:
  language: "en" # Default: en (English)
  speech_rate: 150 # Words per minute (50-300)
  use_google_tts: false # true = online, false = offline
```

| Option           | Type    | Default | Range     | Description                        |
| ---------------- | ------- | ------- | --------- | ---------------------------------- |
| `language`       | string  | "en"    | See below | Default language on startup        |
| `speech_rate`    | integer | 150     | 50-300    | Speaking speed (WPM)               |
| `use_google_tts` | boolean | false   | -         | Use Google TTS (requires internet) |

### Language Profiles

```yaml
speech:
  languages:
    en:
      name: "English"
      voice_id: 0
      gtts_lang: "en"
      recognition_lang: "en-US"
    id:
      name: "Indonesian"
      voice_id: 0
      gtts_lang: "id"
      recognition_lang: "id-ID"
    es:
      name: "Spanish"
      voice_id: 0
      gtts_lang: "es"
      recognition_lang: "es-ES"
    fr:
      name: "French"
      voice_id: 0
      gtts_lang: "fr"
      recognition_lang: "fr-FR"
    de:
      name: "German"
      voice_id: 0
      gtts_lang: "de"
      recognition_lang: "de-DE"
    pt:
      name: "Portuguese"
      voice_id: 0
      gtts_lang: "pt"
      recognition_lang: "pt-BR"
    ja:
      name: "Japanese"
      voice_id: 0
      gtts_lang: "ja"
      recognition_lang: "ja-JP"
    zh:
      name: "Mandarin Chinese"
      voice_id: 0
      gtts_lang: "zh-CN"
      recognition_lang: "zh-CN"
```

| Field              | Description             | Notes                           |
| ------------------ | ----------------------- | ------------------------------- |
| `name`             | Display name            | Used in voice feedback          |
| `voice_id`         | Voice index             | 0 = default, 1-5 = alternatives |
| `gtts_lang`        | Google TTS code         | Language code for online TTS    |
| `recognition_lang` | Speech Recognition code | Language for STT                |

### Speech Rate Guide

| Value   | Interpretation | Use Case                        |
| ------- | -------------- | ------------------------------- |
| 50-80   | Very slow      | Elderly users, clarity priority |
| 100-150 | Normal         | General use, recommended        |
| 150-200 | Fast           | Power users, experienced        |
| 200-300 | Very fast      | Advanced users or testing       |

---

## Face Recognition Configuration

```yaml
face_recognition:
  enabled: true
  mode: "hybrid" # hybrid, cloud, local
  model: "hog" # hog (fast) or cnn (accurate)
  detection_confidence: 0.6
  recognition_confidence: 0.6
  max_distance: 0.6
  enable_training: true
  auto_save_encodings: true
  max_faces_per_person: 10
  encoding_model: "resnet" # resnet or vggface2
```

| Option                   | Type   | Default  | Range                | Description                        |
| ------------------------ | ------ | -------- | -------------------- | ---------------------------------- |
| `enabled`                | bool   | true     | -                    | Enable face recognition completely |
| `mode`                   | string | "hybrid" | hybrid, cloud, local | Processing mode                    |
| `model`                  | string | "hog"    | hog, cnn             | Detection method                   |
| `detection_confidence`   | float  | 0.6      | 0.0-1.0              | Face detection threshold           |
| `recognition_confidence` | float  | 0.6      | 0.0-1.0              | Recognition match threshold        |
| `max_distance`           | float  | 0.6      | 0.0-1.0              | Face distance for match            |
| `enable_training`        | bool   | true     | -                    | Allow face enrollment              |
| `auto_save_encodings`    | bool   | true     | -                    | Auto-save trained faces            |
| `max_faces_per_person`   | int    | 10       | 1-50                 | Training samples per person        |
| `encoding_model`         | string | "resnet" | resnet, vggface2     | Encoding algorithm                 |

### Model Comparison

| Model   | Speed        | Accuracy | Resources              | Use Case                   |
| ------- | ------------ | -------- | ---------------------- | -------------------------- |
| **HOG** | Fast (100ms) | 85-90%   | Low (CPU)              | Real-time on weak hardware |
| **CNN** | Slow (300ms) | 95-99%   | High (GPU recommended) | High accuracy, offline     |

### Configuration Profiles

**Real-Time Detection:**

```yaml
face_recognition:
  model: "hog"
  detection_confidence: 0.5
  recognition_confidence: 0.5
  max_distance: 0.7
```

**Accuracy Priority:**

```yaml
face_recognition:
  model: "cnn"
  detection_confidence: 0.8
  recognition_confidence: 0.8
  max_distance: 0.4
```

**Training-Focused:**

```yaml
face_recognition:
  enable_training: true
  max_faces_per_person: 20
  auto_save_encodings: true
```

---

## Sound Localization Configuration

### Main Settings

```yaml
sound_localization:
  enabled: true
  mode: "real-time" # real-time, background, on-demand
  audio_source: "microphone"
  sample_rate: 16000 # Hz
  chunk_size: 1024 # samples
  channels: 1 # 1=mono, 2=stereo
```

| Option         | Type   | Default      | Notes                   |
| -------------- | ------ | ------------ | ----------------------- |
| `enabled`      | bool   | true         | Enable audio processing |
| `mode`         | string | "real-time"  | Processing strategy     |
| `audio_source` | string | "microphone" | Input device            |
| `sample_rate`  | int    | 16000        | Samples/second (Hz)     |
| `chunk_size`   | int    | 1024         | Samples per chunk       |
| `channels`     | int    | 1            | 1=Mono, 2=Stereo        |

### Detection Settings

```yaml
sound_localization:
  detection:
    enabled: true
    min_frequency: 50 # Hz
    max_frequency: 8000 # Hz
    noise_threshold: -40 # dB
    sound_sensitivity: 0.5 # 0.0-1.0
```

| Option              | Type  | Default | Range      | Description                 |
| ------------------- | ----- | ------- | ---------- | --------------------------- |
| `enabled`           | bool  | true    | -          | Enable sound detection      |
| `min_frequency`     | int   | 50      | 20-1000    | Minimum frequency to detect |
| `max_frequency`     | int   | 8000    | 1000-16000 | Maximum frequency           |
| `noise_threshold`   | int   | -40     | -80 to 0   | Noise floor (dB)            |
| `sound_sensitivity` | float | 0.5     | 0.0-1.0    | Detection sensitivity       |

**Noise Threshold Guide:**

| Value | Interpretation | Environment       |
| ----- | -------------- | ----------------- |
| -80   | Very sensitive | Silent room       |
| -60   | Sensitive      | Quiet office      |
| -40   | Normal         | Office/home       |
| -20   | Less sensitive | Noisy environment |
| 0     | Insensitive    | Very loud         |

### Localization Settings

```yaml
sound_localization:
  localization:
    enabled: true
    method: "beamforming" # beamforming, time-difference, phase-shift
    num_directions: 8 # Number of angle bins
    angle_resolution: 45 # Degrees per bin
    max_range: 10 # Meters
```

| Option             | Type   | Default       | Notes                        |
| ------------------ | ------ | ------------- | ---------------------------- |
| `enabled`          | bool   | true          | Enable sound localization    |
| `method`           | string | "beamforming" | Localization algorithm       |
| `num_directions`   | int    | 8             | Angle bins (8=45°, 16=22.5°) |
| `angle_resolution` | int    | 45            | Degrees per section          |
| `max_range`        | float  | 10            | Maximum detection range (m)  |

### Obstacle Detection

```yaml
sound_localization:
  obstacles:
    enabled: true
    detection_timeout: 2.0 # Seconds
    warning_threshold: 2.0 # Meters
    continuous_monitoring: true
```

| Option                  | Type  | Default | Description               |
| ----------------------- | ----- | ------- | ------------------------- |
| `enabled`               | bool  | true    | Enable obstacle detection |
| `detection_timeout`     | float | 2.0     | Timeout for detection     |
| `warning_threshold`     | float | 2.0     | Distance to warn user (m) |
| `continuous_monitoring` | bool  | true    | Continuous scanning       |

**Warning Threshold Guide:**

| Value | Safety Level  | Use Case             |
| ----- | ------------- | -------------------- |
| 1.0m  | Critical      | Crowded environments |
| 2.0m  | Recommended   | General use          |
| 3.0m  | Cautious      | Open spaces          |
| 5.0m  | Early warning | Wide areas           |

### Audio Classification

```yaml
sound_localization:
  audio_classification:
    enabled: true
    classify_sounds: true
    confidence_threshold: 0.7
```

| Option                 | Type  | Default | Description           |
| ---------------------- | ----- | ------- | --------------------- |
| `enabled`              | bool  | true    | Enable classification |
| `classify_sounds`      | bool  | true    | Identify sound types  |
| `confidence_threshold` | float | 0.7     | Min confidence (0-1)  |

### Alerts

```yaml
sound_localization:
  alerts:
    speech_alert: true
    haptic_alert: false
    frequency: 1000 # Hz
    duration: 0.2 # Seconds
```

| Option         | Type  | Default | Description                          |
| -------------- | ----- | ------- | ------------------------------------ |
| `speech_alert` | bool  | true    | Voice alerts enabled                 |
| `haptic_alert` | bool  | false   | Haptic feedback (if device supports) |
| `frequency`    | int   | 1000    | Alert tone frequency (Hz)            |
| `duration`     | float | 0.2     | Alert sound duration (seconds)       |

---

## Vision Configuration

```yaml
vision:
  camera_index: 0
  continuous_mode: false
  detection_confidence: 0.5
  text_confidence: 0.5
```

| Option                 | Type  | Default | Description                |
| ---------------------- | ----- | ------- | -------------------------- |
| `camera_index`         | int   | 0       | Camera device (0=default)  |
| `continuous_mode`      | bool  | false   | Continuous processing      |
| `detection_confidence` | float | 0.5     | Object detection threshold |
| `text_confidence`      | float | 0.5     | OCR confidence threshold   |

---

## Navigation Configuration

```yaml
navigation:
  map_provider: "openstreetmap"
  emergency_alert: true
  audio_guidance: true
  haptic_feedback: false
  voice_directions_frequency: "periodic" # constant, periodic, on-demand
```

| Option                       | Type   | Default         | Description                      |
| ---------------------------- | ------ | --------------- | -------------------------------- |
| `map_provider`               | string | "openstreetmap" | GPS provider                     |
| `emergency_alert`            | bool   | true            | Emergency alerts enabled         |
| `audio_guidance`             | bool   | true            | Audio navigation guidance        |
| `haptic_feedback`            | bool   | false           | Haptic feedback support          |
| `voice_directions_frequency` | string | "periodic"      | Direction announcement frequency |

---

## Environment Variables

Create `.env` file in project root:

```bash
# API Keys
OPENAI_API_KEY=sk-xxxx
GOOGLE_MAPS_API_KEY=xxxx
OPENWEATHER_API_KEY=xxxx

# Database
DATABASE_URL=sqlite:///vision_assistant.db

# Twilio (SMS alerts)
TWILIO_ACCOUNT_SID=xxxxx
TWILIO_AUTH_TOKEN=xxxxx
TWILIO_PHONE_NUMBER=+1234567890

# Emergency Contacts
EMERGENCY_CONTACTS=+1234567890,emergency@email.com

# Debug Mode
DEBUG=false
LOG_LEVEL=INFO
```

**Important:** Never commit `.env` file. Use `.env.example` as template.

---

## Example Configurations

### Lightweight Configuration (Minimal Resources)

For older computers or limited resources:

```yaml
speech:
  language: "en"
  speech_rate: 100
  use_google_tts: false # Offline only

face_recognition:
  model: "hog" # Fast
  detection_confidence: 0.5
  recognition_confidence: 0.5
  max_faces_per_person: 5

sound_localization:
  sample_rate: 8000 # Lower quality
  chunk_size: 512

vision:
  camera_index: 0
  continuous_mode: false
```

### Production Configuration (Accuracy First)

For deployment with good hardware:

```yaml
speech:
  language: "en"
  speech_rate: 150
  use_google_tts: true # Better quality

face_recognition:
  model: "cnn" # Accurate
  detection_confidence: 0.8
  recognition_confidence: 0.8
  max_faces_per_person: 20

sound_localization:
  enabled: true
  mode: "real-time"
  num_directions: 16 # Higher resolution
  warning_threshold: 3.0

vision:
  continuous_mode: true
  detection_confidence: 0.7
```

### Multilingual Configuration (8 Languages)

```yaml
speech:
  language: "id" # Default Indonesian
  languages:
    en:
      name: "English"
      gtts_lang: "en"
      recognition_lang: "en-US"
    id:
      name: "Indonesian"
      gtts_lang: "id"
      recognition_lang: "id-ID"
    es:
      name: "Spanish"
      gtts_lang: "es"
      recognition_lang: "es-ES"
    # ... add other languages
```

### Safety-Focused Configuration

For obstacle avoidance priority:

```yaml
sound_localization:
  obstacles:
    enabled: true
    warning_threshold: 1.5 # Alert at 1.5m
    continuous_monitoring: true
  detection:
    noise_threshold: -50 # Very sensitive
    sound_sensitivity: 0.3

navigation:
  audio_guidance: true
  voice_directions_frequency: "constant"
```

---

## Configuration Validation

Check your configuration:

```bash
# Validate YAML syntax
python -c "
import yaml
with open('config.yaml') as f:
    config = yaml.safe_load(f)
print('✓ Configuration valid')
print(f'Languages: {list(config[\"speech\"][\"languages\"].keys())}')
"

# Test imports with current config
python -c "
from ai_modules.speech_engine import SpeechEngine
se = SpeechEngine()
print(f'✓ Available languages: {list(se.get_available_languages().keys())}')
"
```

---

## Troubleshooting Configuration

| Issue                          | Solution                                    |
| ------------------------------ | ------------------------------------------- |
| YAML parse error               | Check indentation (2 spaces, no tabs)       |
| Language not found             | Verify language code in `speech.languages`  |
| Face recognition slow          | Change model from "cnn" to "hog"            |
| No sound detected              | Lower `noise_threshold` (e.g., -50)         |
| Obstacle warnings too frequent | Increase `warning_threshold`                |
| Commands not recognized        | Check `use_google_tts` for language support |

---

## Performance Impact

| Setting            | Performance Impact | Resource Impact |
| ------------------ | ------------------ | --------------- |
| Model: CNN         | -200ms             | +GPU memory     |
| Language: Multiple | +50ms              | +RAM (small)    |
| Audio: 16kHz       | Baseline           | Baseline        |
| Audio: 44kHz       | -200ms (slower)    | +RAM            |
| TTS: Google        | +300ms             | +Network        |
| TTS: Offline       | Baseline           | +CPU            |

---

## Version Information

- **Version:** 1.1.0
- **Last Updated:** February 11, 2026
- **Config Format:** YAML
- **Environment File:** .env (optional)

For updates and changes: See [CHANGELOG.md](../log/CHANGELOG.md)
