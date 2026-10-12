# System Architecture

## Overview

Vision Assistant is a modular, event-driven architecture designed for accessibility and extensibility. The system uses async/await patterns for responsive non-blocking I/O operations.

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                           │
│                   Voice Commands Input/Output                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
                 ┌───────▼────────┐
                 │  VisionAssistant (app.py)
                 │   Main Orchestrator
                 └───────┬────────┘
                 ┌───────┴────────────────────┐
         ┌───────▼─────────┐          ┌──────▼──────────┐
         │   AI Modules    │          │   Features      │
         │  (ai_modules/)  │          │  (features/)    │
    ┌────┴─────┬────┬─────┴──┐  ┌────┴────┬─────┬────┐
    │           │    │        │  │         │     │    │
┌──▼──┐  ┌────▼─┐ ┌┴────┐ ┌┴┴──┴──┐ ┌──▼──┐ │ ┌┴──┐
│Vision│  │Speech│ │ LLM │ │Neural│ │Nav. │ │ │OCR│
│Proc.│  │Engine│ │Hand.│ │Core  │ │Asst.│ │ └───┘
└───┬──┘  └──┬───┘ └─┬───┘ └─┬────┘ └──┬──┘ │
    │        │       │       │          │    └─ Face Recognition
    │        │       │       │          │
    │        │       │       └─────┬────┘
    └────────┴───────┴─────────────┼────────────┐
                                   │            │
                          ┌────────▼────────┐ ┌─▼──────┐
                          │   Database      │ │External
                          │  (SQLAlchemy)   │ │Services
                          └─────────────────┘ │(APIs)
                                              └───────┘
```

---

## Module Architecture

### 1. Core Application (app.py)

**Responsibility**: Central orchestrator, command routing, and event loop

**Key Components**:

- `VisionAssistant` class - Main entry point
- Async event loop management
- Command to intent mapping
- User session lifecycle

**Design Pattern**: Command Pattern (routes commands to handlers)

```python
async def process_command(command):
    intent = llm.understand_intent(command)
    # Route based on intent['action']
    handler = handlers[intent['action']]
    await handler(intent['parameters'])
```

---

### 2. AI Modules (ai_modules/)

#### Vision Processor (vision_processor.py)

**Responsibility**: Computer vision operations

**Architecture**:

```
Input Image
    │
    ├─→ YOLOv8 Detection ─→ Object List
    │
    ├─→ EasyOCR ─→ Text Extraction
    │
    ├─→ Haar Cascades ─→ Face Detection
    │
    └─→ Scene Describer ─→ Narrative
```

**Key Features**:

- Lazy initialization of models (loaded on first use)
- Error handling with fallbacks
- Configurable detection confidence
- Batch processing support

**Dependencies**:

```
OpenCV ──┐
         ├─→ Vision Processor ─→ JSON Output
YOLOv8 ──┤
EasyOCR ─┤
         └─→ Numpy arrays
```

---

#### Speech Engine (speech_engine.py)

**Responsibility**: Audio input/output and TTS/STT

**Architecture**:

```
User Voice Input
       │
       ├─→ pyaudio (Capture)
       │
       ├─→ SpeechRecognition (Google API)
       │
       └─→ Text Output
           │
           ├─→ pyttsx3 (Offline TTS) ─→ Local Speaker
           │
           └─→ gTTS (Online TTS) ─→ Network Speaker
```

**Configuration Options**:

- Language selection (default: 'en')
- TTS provider (pyttsx3 vs gTTS)
- Speech rate adjustment (50-300 WPM)
- Recognition timeout

---

#### LLM Handler (llm_handler.py)

**Responsibility**: Intent recognition and response generation

**Architecture**:

```
User Command
    │
    ├─→ Keyword Matching (Local) ─┐
    │                             │
    └─→ OpenAI API (Cloud) ───────┼─→ Intent Classification
                                  │
                    ┌─────────────┘
                    │
                    ▼
         Intent Dictionary
         {action, parameters}
            │
            ├─→ Response Generation
            │
            └─→ Context Enrichment
```

**Intent Types**:

- `describe_scene` - Visual analysis
- `read_text` - OCR operations
- `recognize_objects` - Object detection
- `navigate` - GPS assistance
- `recognize_people` - Face detection
- `emergency` - Alert handling
- `exit` - Graceful shutdown
- `general_question` - Q&A

**Fallback Strategy**:

1. Try OpenAI API → successful return
2. Fall back to keyword matching (local)
3. Fall back to "I'm not sure" response

---

#### Neural Core (neural_core.py)

**Responsibility**: Model management and device optimization

**Features**:

- CUDA/CPU selection
- Model caching and lazy loading
- Memory management
- Device compatibility checking

```python
# Device selection logic
if torch.cuda.is_available():
    device = 'cuda'
else:
    device = 'cpu'
```

---

### 3. Features (features/)

Independent modules that build on AI modules.

#### Navigation Assistant (navigation.py)

**Capabilities**:

- Current location retrieval
- Route planning
- Nearby location discovery
- Turn-by-turn directions

**External Dependencies**:

- Google Maps API (optional)

#### Object Detection (object_detection.py)

**Wrapper** around vision processor for convenience.

#### Text Reader (text_reader.py)

**OCR Pipeline** with:

- Text extraction
- Reading experience (pause/resume)
- Text storage and retrieval

#### Face Recognition (face_recognition.py)

**Face operations**:

- Detection
- Tracking
- Identity matching (placeholder)

---

### 4. Database Layer (database/)

**ORM**: SQLAlchemy 2.0+

**Schema**:

```
┌───────────────┐
│     User      │
├───────────────┤
│ user_id (PK)  │
│ name          │
│ email         │
│ language      │
│ speech_rate   │
│ preferences   │
└───────┬───────┘
        │ 1:Many
        ├─→ SceneMemory (location history)
        ├─→ ConversationHistory (chat logs)
        ├─→ TextExtraction (saved text)
        └─→ ObjectDetection (object history)
```

**Operations**:

- Async session management
- User preference persistence
- History tracking
- Query optimization

---

## Data Flow Diagrams

### Voice Command Processing

```
User speaks "Describe my surroundings"
            │
            ▼
     Speech Recognition
     (Google API)
            │
            ▼
Text: "Describe my surroundings"
            │
            ▼
    LLM Intent Analysis
            │
            ▼
Intent: {action: 'describe_scene', parameters: {detailed: false}}
            │
            ▼
      Vision Processor
      - Capture image
      - Run YOLOv8
      - Run EasyOCR
      - Run Face Detection
            │
            ▼
   Results: {objects: [...], text: [...], faces: [...]}
            │
            ▼
   Response Generation
   "I see 2 people and text reading..."
            │
            ▼
      Text-to-Speech
            │
            ▼
   User hears response
```

---

### Database Persistence

```
Command Execution
       │
       ├─→ Save to History
       │   └─→ ConversationHistory Table
       │
       ├─→ Cache Results
       │   └─→ SceneMemory Table
       │
       └─→ Update Preferences
           └─→ User Preferences
```

---

## Design Patterns Used

### 1. Singleton Pattern

- NeuralCore (single model cache)
- DatabaseHandler (single DB connection)

### 2. Command Pattern

- Intent routing in app.py
- Modular handlers for each intent type

### 3. Factory Pattern

- Vision model creation (YOLOv8, EasyOCR)
- TTS engine selection

### 4. Observer Pattern

- Voice commands trigger callbacks
- Event-driven architecture

### 5. Adapter Pattern

- Speech API wrapper (SpeechRecognition)
- LLM API wrapper (OpenAI)

---

## Async/Await Architecture

All I/O operations are non-blocking:

```python
# Non-blocking speech capture
command = await speech_engine.listen()

# Non-blocking vision processing
objects = await vision_processor.detect_objects(frame)

# Non-blocking LLM inference
intent = await llm_handler.understand_intent(command)

# Non-blocking database operations
await db_handler.save_conversation(user_id, input, output)
```

**Benefits**:

- Responsive to user input
- Better resource utilization
- Handles multiple operations concurrently
- Non-freezing UI/voice

---

## Configuration Management

```
config.yaml (application defaults)
    │
    ├─→ Loaded at startup
    │
.env (environment variables)
    │
    ├─→ Overrides config.yaml
    │
    └─→ Optional API keys and secrets
```

**Hierarchy**:

1. Default hardcoded values
2. config.yaml settings
3. .env variables (highest priority)

---

## Error Handling Strategy

### Level 1: Module Level

```python
try:
    result = await vision_processor.detect_objects(image)
except Exception as e:
    log_error(e)
    speak("Could not analyze image")
```

### Level 2: Application Level

```python
try:
    await assistant.process_command(command)
except sr.RequestError:
    speak("Microphone connection failed")
except Exception as e:
    speak("Unexpected error occurred")
```

### Level 3: Global Error Handler

```python
async def handle_exception(exc):
    log_error(exc)
    speak("System error")
    await assistant.handle_exit()
```

---

## Performance Considerations

### Model Optimization

- Use nano/small models for faster inference
- Batch processing when possible
- GPU acceleration with CUDA if available

### Memory Management

- Lazy model loading
- Cache cleanup on exit
- Resource pooling

### Latency Targets

- Voice command response: <2s
- Object detection: <200ms
- Speech recognition: <1s
- TTS: varies by text length

---

## Security Architecture

### API Keys

- Stored in .env (not committed)
- Loaded at runtime
- Passed securely to services

### User Data

- Stored locally in SQLAlchemy ORM
- Optional cloud sync (not implemented)
- Encrypted storage (future)

### Third-Party APIs

- All calls over HTTPS
- Rate limiting implemented
- Error recovery without exposing internals

---

## Deployment Architecture

### Development

- Local virtual environment
- SQLite database
- Optional GPU (CUDA)

### Production (Future)

- Docker containerization
- Cloud deployment
- Distributed database
- Load balancing

### Mobile (Future)

- Model quantization
- On-device inference
- Minimal cloud dependency

---

## Extension Points

### Adding New Intent Handler

1. Add to keyword dictionary in llm_handler.py
2. Create handler method in app.py
3. Call associated feature/module
4. Return result and voice feedback

### Adding New Vision Feature

1. Create method in vision_processor.py
2. Wrap in features/
3. Add intent mapping
4. Test with images

### Adding New External Service

1. Create adapter module in api_integration/
2. Handle API key configuration
3. Implement error fallbacks
4. Add to appropriate handler

---

## See Also

- [README.md](../README.md) - Project overview
- [API.md](API.md) - API reference
- [CONTRIBUTING.md](./guidelines/CONTRIBUTING.md) - Contributing guidelines
