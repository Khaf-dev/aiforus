# API Reference

## Vision Assistant Core Classes

### VisionAssistant

Main application class that orchestrates all components.

```python
class VisionAssistant:
    def __init__(self)
    async def continuous_assistant()
    async def process_command(command: str)
    async def describe_environment(detailed=False)
    async def read_text_around()
    async def identify_objects()
    async def recognize_faces()
    async def assist_navigation(parameters)
    async def handle_emergency()
    async def handle_exit()
    def stop()
```

#### Methods

**`__init__()`**

- Initializes all core modules (vision, speech, LLM, database, navigation)
- Sets up user preferences and context
- Starts background services

**`async continuous_assistant()`**

- Main event loop listening for voice commands
- Processes commands until user exits
- Handles errors gracefully

Example:

```python
assistant = VisionAssistant()
await assistant.continuous_assistant()
```

**`async process_command(command: str)`**

- Parses voice command intent
- Routes to appropriate handler
- Provides voice feedback

Example:

```python
await assistant.process_command("What do you see?")
```

---

### VisionProcessor

Computer vision module for image analysis.

```python
class VisionProcessor:
    def __init__()
    def capture_image(save_path=None) -> np.ndarray
    async def describe_scene_detailed(image) -> str
    async def describe_scene_brief(image) -> str
    async def detect_objects(image) -> List[Dict]
    async def extract_text(image) -> List[str]
    async def recognize_faces(image) -> List[Dict]
    def cleanup()
```

#### Methods

**`capture_image(save_path=None) -> np.ndarray`**

- Captures image from camera
- Optionally saves to file
- Returns numpy array (RGB or None)

Example:

```python
vp = VisionProcessor()
frame = vp.capture_image()
if frame is not None:
    objects = await vp.detect_objects(frame)
```

**`async detect_objects(image) -> List[Dict]`**

- Uses YOLOv8 for object detection
- Returns list of detected objects

Returns:

```python
[
    {
        'name': 'person',
        'confidence': 0.95,
        'bbox': [x1, y1, x2, y2]
    },
    # ...
]
```

**`async extract_text(image) -> List[str]`**

- Uses EasyOCR for text recognition
- Returns list of detected text strings

Example:

```python
texts = await vp.extract_text(frame)
# ['Hello', 'World', '42']
```

**`async recognize_faces(image) -> List[Dict]`**

- Uses OpenCV face detection
- Returns face locations and metadata

Returns:

```python
[
    {
        'bbox': [x, y, w, h],
        'name': 'Unknown',
        'confidence': 0.0
    }
]
```

---

### SpeechEngine

Voice input/output for natural interaction.

```python
class SpeechEngine:
    def __init__(language="en")
    async def listen(timeout=10) -> Optional[str]
    def speak(text: str)
    def set_language(language: str)
```

#### Methods

**`async listen(timeout=10) -> Optional[str]`**

- Records audio from microphone
- Converts to text via speech recognition
- Returns transcribed command

Example:

```python
se = SpeechEngine()
command = await se.listen()
# Output: "What do you see?"
```

**`speak(text: str)`**

- Converts text to speech
- Plays audio immediately
- Blocks until speech complete

Example:

```python
se.speak("I can see a person")
```

---

### LLMHandler

Language model for intent recognition and response generation.

```python
class LLMHandler:
    def __init__(use_openai=True)
    async def understand_intent(command: str, context: Dict) -> Dict
    async def generate_response(query: str, context: Dict) -> str
    async def generate_scene_description(objects: List, texts: List, context: Dict) -> str
```

#### Methods

**`async understand_intent(command: str, context: Dict) -> Dict`**

- Parses user command intent
- Extracts parameters
- Uses OpenAI or local keyword matching

Returns:

```python
{
    'action': 'describe_scene',
    'parameters': {'detailed': True}
}
```

Supported intents:

- `describe_scene` - Scene analysis
- `read_text` - Text recognition
- `recognize_objects` - Object identification
- `navigate` - Navigation assistance
- `recognize_people` - Face detection
- `emergency` - Emergency alert
- `exit` - Exit application
- `general_question` - General Q&A

**`async generate_response(query: str, context: Dict) -> str`**

- Generates natural language response
- Uses OpenAI or local model

Example:

```python
response = await llm.generate_response("How are you?")
# Output: "I'm functioning well..."
```

---

### DatabaseHandler

Persistent data storage for user preferences and history.

```python
class DatabaseHandler:
    def __init__(db_path)
    def get_user_preferences(user_id=1) -> Dict
    def update_user_preferences(preferences: Dict, user_id=1)
    def save_scene_memory(user_id, location, description, objects)
    def get_location_history(user_id, limit=10) -> List
    def save_conversation(user_id, user_input, assistant_response)
    def get_conversation_history(user_id, limit=20) -> List
    def close()
```

#### Methods

**`get_user_preferences(user_id=1) -> Dict`**

- Retrieves user settings and preferences

Example:

```python
prefs = db.get_user_preferences()
# {
#     'speech_rate': 150,
#     'language': 'en',
#     'continuous_mode': False,
#     ...
# }
```

**`save_conversation(user_id, user_input, assistant_response)`**

- Stores conversation for history/training

---

### NavigationAssistant

GPS-based navigation and directions.

```python
class NavigationAssistant:
    async def get_current_location() -> Dict
    async def get_directions(start, destination) -> Dict
    async def get_nearby_locations(location, radius=1000) -> List
```

#### Methods

**`async get_current_location() -> Dict`**

- Gets current GPS location
- Returns coordinates and address

Returns:

```python
{
    'latitude': 40.7128,
    'longitude': -74.0060,
    'address': '123 Main St, New York, NY'
}
```

**`async get_directions(start, destination) -> Dict`**

- Calculates route between locations
- Returns step-by-step directions

Returns:

```python
{
    'distance': 2.5,  # km
    'duration': 15,   # minutes
    'steps': [
        {
            'instruction': 'Head northwest on Main St',
            'distance': 0.5,
            'duration': 3
        },
        # ...
    ]
}
```

---

## Configuration

### Environment Variables

```python
OPENAI_API_KEY          # OpenAI API key (optional)
SPEECH_LANGUAGE         # Language code (default: 'en')
SPEECH_RATE             # Words per minute (default: 150)
DEVICE                  # 'cpu' or 'cuda' (default: 'cpu')
DATABASE_URL            # Database connection string
```

### Configuration File (config.yaml)

```yaml
app:
  name: Vision Assistant
  debug: false
  version: 1.0.0

speech:
  language: en
  speech_rate: 150
  use_google_tts: false

ai:
  llm_provider: openai # or 'local'
  vision_model: yolov8n
  text_model: easyocr
  device: cpu
```

---

## Examples

### Basic Usage

```python
import asyncio
from app import VisionAssistant

async def main():
    assistant = VisionAssistant()
    await assistant.continuous_assistant()

asyncio.run(main())
```

### Programmatic Usage

```python
from app import VisionAssistant
import asyncio

async def analyze_scene():
    assistant = VisionAssistant()

    # Describe environment
    await assistant.describe_environment(detailed=True)

    # Read text
    await assistant.read_text_around()

    # Identify objects
    await assistant.identify_objects()

    # Recognize faces
    await assistant.recognize_faces()

asyncio.run(analyze_scene())
```

### Custom Vision Processing

```python
from ai_modules.vision_processor import VisionProcessor
import asyncio

async def custom_vision():
    vp = VisionProcessor()

    # Capture image
    frame = vp.capture_image()

    # Detect objects
    objects = await vp.detect_objects(frame)
    print(f"Found {len(objects)} objects")

    # Extract text
    texts = await vp.extract_text(frame)
    print(f"Text: {texts}")

    # Cleanup
    vp.cleanup()

asyncio.run(custom_vision())
```

---

## Error Handling

```python
try:
    command = await speech_engine.listen()
    if command:
        await assistant.process_command(command)
except sr.RequestError:
    print("Speech recognition service unavailable")
except sr.UnknownValueError:
    print("Could not understand audio")
except Exception as e:
    print(f"Error: {e}")
```

---

## Performance Considerations

- Use `device='cuda'` for GPU acceleration if available
- Cache models during initialization (NeuralCore)
- Batch process multiple images when possible
- Use appropriate model sizes (nano, small, medium)

---

## See Also

- [README.md](../README.md) - Project overview
- [INSTALLATION.md](INSTALLATION.md) - Setup guide
- [CONTRIBUTING.md](../CONTRIBUTING.md) - Development guidelines
