# Complete API Reference v1.1

## Table of Contents

1. [Core Application](#core-application)
2. [Vision Processor](#vision-processor)
3. [Speech Engine](#speech-engine)
4. [LLM Handler](#llm-handler)
5. [Face Recognizer](#face-recognizer)
6. [Sound Localizer](#sound-localizer)
7. [Navigation](#navigation)
8. [Database Handler](#database-handler)

---

## Core Application

### VisionAssistant Class

Main orchestrator for all Vision Assistant features.

#### Initialization

```python
from app import VisionAssistant

# Create assistant
assistant = VisionAssistant(language: Optional[str] = None)

# Parameters:
# - language: Language code ('en', 'es', 'id', 'fr', 'de', 'pt', 'ja', 'zh')
#            Defaults to config.yaml setting if None
```

#### Methods

##### `continuous_assistant()`

Main async event loop for continuous assistance.

```python
await assistant.continuous_assistant()
# Listens for voice commands indefinitely
# Returns: Never (runs until KeyboardInterrupt)
```

##### `process_command(command: str)`

Process a voice command with LLM intent recognition.

```python
result = await assistant.process_command("What's in front of me?")
# Returns: Dictionary with intent, response, context
```

##### `recognize_faces(frame)`

Detect and recognize faces in a frame.

```python
faces = await assistant.recognize_faces(frame)
# Parameters:
#   frame: numpy array (opencv frame)
# Returns: [{'name': str, 'confidence': float, 'distance': float}]
```

##### `assist_navigation(destination: str)`

Provide navigation assistance with audio cues.

```python
guidance = await assistant.assist_navigation("nearest cafe")
# Parameters:
#   destination: Location or POI name
# Returns: Directions with audio guidance
```

##### `handle_emergency()`

Trigger emergency alert system.

```python
await assistant.handle_emergency()
# Sends alerts to emergency contacts
# Returns: None
```

---

## Vision Processor

### VisionProcessor Class

Handles all computer vision operations.

#### Initialization

```python
from ai_modules.vision_processor import VisionProcessor

processor = VisionProcessor()
```

#### Methods

##### `capture_image()`

Capture image from camera.

```python
frame = processor.capture_image()
# Returns: numpy array (BGR format)
```

##### `detect_objects(frame, confidence: float = 0.5)`

Detect objects using YOLOv8.

```python
objects = processor.detect_objects(frame, confidence=0.6)
# Parameters:
#   frame: numpy array
#   confidence: Detection threshold (0-1)
# Returns: [{'name': str, 'confidence': float, 'box': (x,y,w,h)}]
```

##### `extract_text(frame, language: str = 'en')`

Extract text using OCR.

```python
text_data = processor.extract_text(frame, language='es')
# Parameters:
#   frame: numpy array
#   language: Language code for OCR
# Returns: [{'text': str, 'confidence': float, 'location': (x,y,w,h)}]
```

##### `describe_scene(frame, objects: list = None)`

Generate natural language scene description.

```python
description = processor.describe_scene(frame, objects)
# Parameters:
#   frame: numpy array
#   objects: Optional list of detected objects
# Returns: str (Scene description)
```

---

## Speech Engine

### SpeechEngine Class

Handles speech recognition and synthesis.

#### Initialization

```python
from ai_modules.speech_engine import SpeechEngine

speech = SpeechEngine(language: str = 'en')
# Parameters:
#   language: Language code for TTS/STT
```

#### Methods

##### `speak(text: str, use_google: Optional[bool] = None)`

Convert text to speech.

```python
speech.speak("Hello, how can I help?", use_google=False)
# Parameters:
#   text: Text to be spoken
#   use_google: Use Google TTS (True) or offline (False)
# Returns: None
```

##### `listen(timeout: int = 5)`

Async listen for voice command.

```python
command = await speech.listen(timeout=10)
# Parameters:
#   timeout: Max seconds to listen
# Returns: str (recognized text) or None
```

##### `set_language(lang_code: str)`

Switch language at runtime.

```python
speech.set_language('es')
# Parameters:
#   lang_code: Language code
# Returns: None
```

##### `get_available_languages()`

Get all supported languages.

```python
languages = speech.get_available_languages()
# Returns: {'en': 'English', 'es': 'Spanish', ...}
```

##### `get_language_name(code: Optional[str] = None)`

Get readable language name.

```python
name = speech.get_language_name('pt')
# Returns: 'Portuguese'
```

##### `setup_tts()`

Configure TTS engine.

```python
speech.setup_tts()
# Sets up pyttsx3 with language-specific voice
# Returns: None
```

---

## LLM Handler

### LLMHandler Class

Handles AI intent recognition and response generation.

#### Initialization

```python
from ai_modules.llm_handler import LLMHandler

llm = LLMHandler()
```

#### Methods

##### `understand_intent(command: str, language: str = 'en')`

Parse command to identify intent.

```python
intent = await llm.understand_intent("Navigate to the cafe", language='en')
# Returns: {
#   'intent': 'navigation',
#   'parameters': {'destination': 'cafe'},
#   'confidence': 0.95
# }
```

##### `generate_response(intent: dict, context: dict = None)`

Generate contextual response.

```python
response = await llm.generate_response(
    intent={'intent': 'greeting'},
    context={'person': 'John', 'language': 'en'}
)
# Returns: str (AI response)
```

##### `get_command_suggestions(current_input: str)`

Suggest next commands.

```python
suggestions = llm.get_command_suggestions("Who is")
# Returns: ['Who is in front?', 'Who just arrived?']
```

---

## Face Recognizer

### FaceRecognizer Class

Face detection and recognition with enrollment.

#### Initialization

```python
from features.face_recognition import FaceRecognizer

recognizer = FaceRecognizer(enable_recognition: bool = True)
# Parameters:
#   enable_recognition: Enable person recognition (True) or only detection
```

#### Methods

##### `detect_faces(frame)`

Detect all faces in frame.

```python
faces = recognizer.detect_faces(frame)
# Returns: [{
#   'location': (top, right, bottom, left),
#   'encoding': numpy_array,
#   'landmarks': {...}
# }]
```

##### `recognize_faces(frame, faces: list = None)`

Identify detected faces.

```python
matches = recognizer.recognize_faces(frame, faces)
# Returns: [{
#   'name': 'John',
#   'confidence': 0.95,
#   'distance': 0.35
# }]
```

##### `enroll_face(person_name: str, num_samples: int = 5)`

Enroll new person with multiple samples.

```python
success = await recognizer.enroll_face('John', num_samples=5)
# Parameters:
#   person_name: Name of person to enroll
#   num_samples: Number of samples to capture
# Returns: bool (Success)
```

##### `enroll_from_image(person_name: str, image_path: str)`

Enroll from single image file.

```python
success = recognizer.enroll_from_image('John', '/path/to/photo.jpg')
# Returns: bool (Success)
```

##### `get_known_people()`

List all enrolled people.

```python
people = recognizer.get_known_people()
# Returns: ['John', 'Sarah', 'Mom']
```

##### `remove_person(person_name: str)`

Delete person from enrollment.

```python
recognizer.remove_person('John')
# Returns: None
```

##### `get_statistics()`

Get enrollment statistics.

```python
stats = recognizer.get_statistics()
# Returns: {
#   'total_people': 5,
#   'total_encodings': 25,
#   'avg_encodings_per_person': 5.0
# }
```

##### `get_face_description(faces: list)`

Generate description of detected faces.

```python
description = recognizer.get_face_description(faces)
# Returns: "Two people detected. Male on left, female on right."
```

---

## Sound Localizer

### SoundLocalizer Class

Real-time audio detection, localization, and obstacle detection.

#### Initialization

```python
from ai_modules.sound_localization import SoundLocalizer

localizer = SoundLocalizer()
```

#### Methods

##### `start_listening()`

Start audio stream.

```python
success = localizer.start_listening()
# Returns: bool (Success)
```

##### `stop_listening()`

Stop audio stream.

```python
localizer.stop_listening()
# Returns: None
```

##### `detect_sounds()`

Detect audio events in current stream.

```python
sounds = await localizer.detect_sounds()
# Returns: [{
#   'frequency': 1500,
#   'power': 0.85,
#   'timestamp': datetime
# }]
```

##### `localize_sound(audio_chunk)`

Estimate direction and distance of sound.

```python
localization = localizer.localize_sound(audio_chunk)
# Returns: {
#   'direction': 'Right',
#   'angle': 90,
#   'distance': 5.0,
#   'confidence': 0.85
# }
```

##### `detect_obstacles(audio_chunk)`

Detect obstacles via echo analysis.

```python
obstacles = localizer.detect_obstacles(audio_chunk)
# Returns: [{
#   'direction': 'Right',
#   'distance': 2.5,
#   'type': 'hard_surface',
#   'confidence': 0.75
# }]
```

##### `classify_sound(audio_chunk)`

Identify sound type.

```python
sound_type = localizer.classify_sound(audio_chunk)
# Returns: 'vehicle' | 'speech' | 'alarm' | 'noise' | 'unknown'
```

##### `get_audio_description()`

Generate narrative description of audio scene.

```python
description = localizer.get_audio_description()
# Returns: "Vehicle alarm on your right, 5 meters away. Distant traffic."
```

##### `get_localization_summary()`

Get directional summary.

```python
summary = localizer.get_localization_summary()
# Returns: "Front: Clear (speech), Right: Vehicle (5m), Back: Clear"
```

##### `get_audio_chunk()`

Get raw audio data.

```python
chunk = localizer.get_audio_chunk()
# Returns: numpy array or None
```

---

## Navigation

### NavigationAssistant Class

GPS, routing, and audio-guided navigation.

#### Initialization

```python
from features.navigation import NavigationAssistant

navigation = NavigationAssistant()
```

#### Methods

##### `get_current_location()`

Get device location.

```python
location = await navigation.get_current_location()
# Returns: {
#   'latitude': 51.5074,
#   'longitude': -0.1278,
#   'address': '123 Main St, London'
# }
```

##### `get_directions(start: str, destination: str)`

Get route directions.

```python
directions = await navigation.get_directions(
    start='Current location',
    destination='Nearest hospital'
)
# Returns: {
#   'distance': 2.5,
#   'duration': 15,
#   'steps': [
#     {'instruction': 'Go north', 'distance': 0.5},
#     ...
#   ]
# }
```

##### `get_nearby_places(category: str, radius: float = 1000)`

Find nearby points of interest.

```python
places = await navigation.get_nearby_places('cafe', radius=500)
# Returns: [{
#   'name': 'Coffee Corner',
#   'distance': 200,
#   'direction': 'North',
#   'address': '...'
# }]
```

##### `get_audio_guidance()`

Get navigation with audio cues.

```python
guidance = await navigation.get_audio_guidance()
# Returns: Dict with turn-by-turn audio directions
```

##### `assist_with_obstacles(obstacles: list)`

Provide obstacle information.

```python
assistance = await navigation.assist_with_obstacles([
    {'direction': 'Right', 'distance': 2.0}
])
# Returns: str (Warning/advice)
```

##### `set_audio_guidance(enabled: bool)`

Toggle sound-guided navigation.

```python
navigation.set_audio_guidance(True)
# Returns: None
```

---

## Database Handler

### DatabaseHandler Class

Data persistence and retrieval.

#### Initialization

```python
from database.db_handler import DatabaseHandler

db = DatabaseHandler(db_path='vision_assistant.db')
```

#### Methods

##### `get_user_preferences(user_id: int = 1)`

Retrieve user settings.

```python
prefs = db.get_user_preferences()
# Returns: {
#   'language': 'en',
#   'speech_rate': 150,
#   'detail_level': 'normal'
# }
```

##### `save_conversation(user_id: int, user_input: str, response: str)`

Log conversation.

```python
db.save_conversation(1, "What's ahead?", "I see...")
# Returns: None
```

##### `get_conversation_history(user_id: int, limit: int = 20)`

Retrieve past conversations.

```python
history = db.get_conversation_history(1, limit=10)
# Returns: [{
#   'user_input': 'What is this?',
#   'assistant': 'This is a coffee cup',
#   'timestamp': '2024-01-15T10:30:00'
# }]
```

##### `add_known_face(user_id: int, name: str, face_data: dict)`

Store face encoding.

```python
db.add_known_face(1, 'John', {'encoding': array})
# Returns: None
```

##### `get_known_faces(user_id: int)`

Retrieve enrolled faces.

```python
faces = db.get_known_faces(1)
# Returns: [{'name': 'John', 'encodings': [...]}]
```

##### `send_emergency_alert(emergency_contacts: list)`

Send emergency notification.

```python
success = await db.send_emergency_alert(
    ['+1234567890', 'email@example.com']
)
# Returns: bool (Success)
```

##### `close()`

Close database connection.

```python
db.close()
# Returns: None
```

---

## Data Models

### User

```python
class User(Base):
    id: int (Primary Key)
    name: str
    email: str
    language: str
    speech_rate: int
    preferences: dict
    emergency_contacts: list
```

### ConversationHistory

```python
class ConversationHistory(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    user_input: str
    assistant_response: str
    intent: str
    confidence: float
    timestamp: datetime
```

### SceneMemory

```python
class SceneMemory(Base):
    id: int (Primary Key)
    user_id: int (Foreign Key)
    scene_description: str
    objects_detected: list
    location: str
    timestamp: datetime
```

### Person (Face Recognition)

```python
class Person(Base):
    id: int (Primary Key)
    person_name: str
    relationship: str
    notes: str
    enrollment_date: datetime
```

### FaceEncoding

```python
class FaceEncoding(Base):
    id: int (Primary Key)
    person_id: int (Foreign Key)
    encoding: bytes
    confidence: float
    source: str
    metadata: dict
```

---

## Common Usage Patterns

### Complete Conversation Loop

```python
# Initialize
assistant = VisionAssistant(language='en')

# Listen for command
command = await assistant.speech.listen()

# Understand intent
intent = await assistant.llm.understand_intent(command)

# Process based on intent
if intent['intent'] == 'object_detection':
    frame = assistant.vision.capture_image()
    objects = assistant.vision.detect_objects(frame)
    description = assistant.vision.describe_scene(frame, objects)

# Respond
assistant.speech.speak(description)
```

### Face Recognition Loop

```python
# Enroll
await assistant.face_recognizer.enroll_face('John')

# Recognize
frame = assistant.vision.capture_image()
faces = assistant.face_recognizer.detect_faces(frame)
matches = assistant.face_recognizer.recognize_faces(frame, faces)

# Respond
if matches:
    greeting = f"Hello, {matches[0]['name']}!"
else:
    greeting = "I see someone new!"
assistant.speech.speak(greeting)
```

### Navigation with Obstacles

```python
# Start
location = await assistant.navigation.get_current_location()

# Get route
directions = await assistant.navigation.get_directions(
    location['address'],
    'nearest hospital'
)

# Listen for obstacles
assistant.sound_localizer.start_listening()

# Guide with awareness
for step in directions['steps']:
    audio_chunk = assistant.sound_localizer.get_audio_chunk()
    obstacles = assistant.sound_localizer.detect_obstacles(audio_chunk)

    if obstacles:
        warning = await assistant.navigation.assist_with_obstacles(obstacles)
        assistant.speech.speak(warning)

    assistant.speech.speak(step['instruction'])
```

---

## Error Handling

### Common Exceptions

```python
# ImportError
try:
    from ai_modules.vision_processor import VisionProcessor
except ImportError as e:
    logger.error(f"Failed to import: {e}")

# No camera/microphone
try:
    frame = vision.capture_image()
except RuntimeError as e:
    logger.warning(f"Camera error: {e}")

# Network timeout
try:
    location = await navigation.get_current_location()
except TimeoutError:
    logger.warning("Network timeout, using cached location")

# Database errors
try:
    db.save_conversation(user_id, input, response)
except Exception as e:
    logger.error(f"Database error: {e}")
```

---

## Configuration Constants

Available in `config.yaml`:

```yaml
# Speech
LANGUAGES: ["en", "es", "id", "fr", "de", "pt", "ja", "zh"]
SPEECH_RATE: 150 # words per minute

# Vision
DETECTION_CONFIDENCE: 0.5
OCR_LANGUAGE: "en"

# Face Recognition
FACE_CONFIDENCE: 0.6
MAX_PEOPLE: 20

# Sound Localization
NOISE_THRESHOLD: -40 # dB
NUM_DIRECTIONS: 8
MAX_RANGE: 10 # meters
```
