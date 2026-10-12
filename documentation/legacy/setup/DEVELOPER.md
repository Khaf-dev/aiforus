# Developer Guide

Guide for developers extending and contributing to Vision Assistant.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Adding Features](#adding-features)
4. [Code Standards](#code-standards)
5. [Testing](#testing)
6. [Debugging](#debugging)
7. [Git Workflow](#git-workflow)
8. [Performance Profiling](#performance-profiling)

---

## Development Setup

### Clone & Setup

```bash
# Clone repository
git clone <repository-url>
cd aiforus

# Create virtual environment
python -m venv venv

# Activate
# Windows
venv\Scripts\activate
# Linux/macOS
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Install development tools
pip install pytest black flake8 mypy pytest-cov
```

### IDE Setup

**VS Code** (`settings.json`):

```json
{
  "python.defaultInterpreterPath": "${workspaceFolder}/venv/bin/python",
  "python.formatting.provider": "black",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.linting.flake8Args": ["--max-line-length=100"],
  "editor.formatOnSave": true,
  "[python]": {
    "editor.defaultFormatter": "ms-python.python",
    "editor.formatOnSave": true
  }
}
```

**PyCharm**:

1. Set interpreter: Settings → Project → Python Interpreter → venv
2. Enable code inspection: Settings → Editor → Inspections
3. Configure code style: Settings → Editor → Code Style → Python

---

## Project Structure

### Directory Organization

```
aiforus/
├── app.py                    # Main application (200+ lines)
├── config.yaml              # Configuration
├── requirements.txt         # Dependencies
├── .env.example              # Secrets template
│
├── ai_modules/              # Core AI processing
│   ├── __init__.py
│   ├── vision_processor.py   # Computer vision (YOLOv8, EasyOCR)
│   ├── speech_engine.py      # Voice I/O
│   ├── llm_handler.py        # Intent recognition & LLM
│   └── neural_core.py        # Model management
│
├── features/                # High-level features
│   ├── __init__.py
│   ├── navigation.py         # GPS & directions
│   ├── object_detection.py   # Wrapper around vision_processor
│   ├── text_reader.py        # OCR pipeline
│   └── face_recognition.py   # Face detection/recognition
│
├── database/                # Data persistence
│   ├── __init__.py
│   ├── models.py             # SQLAlchemy ORM models
│   └── db_handler.py         # Database operations
│
├── api_integration/         # External service adapters
│   └── __init__.py
│
├── tests/                   # Unit tests
│   ├── __init__.py
│   └── test_*.py             # Test files
│
├── documentation/           # All docs
│   ├── README.md
│   ├── INSTALLATION.md
│   ├── API.md
│   ├── ARCHITECTURE.md
│   ├── TROUBLESHOOTING.md
│   ├── DEPLOYMENT.md
│   ├── QUICKREF.md
│   └── DEVELOPER.md (this file)
│
└── .github/
    └── copilot-instructions.md
```

---

## Adding Features

### Adding a New Vision Feature

**Step 1: Implement in VisionProcessor**

```python
# ai_modules/vision_processor.py

async def detect_colors(self, image: np.ndarray) -> Dict[str, int]:
    """Detect dominant colors in image.

    Args:
        image: Input image (numpy array)

    Returns:
        Dictionary mapping color names to percentages
    """
    # Convert to HSV for better color detection
    hsv = cv2.cvtColor(image, cv2.COLOR_RGB2HSV)

    # Define color ranges
    colors = {
        'red': [(0, 100, 100), (10, 255, 255)],
        'green': [(35, 100, 100), (85, 255, 255)],
        'blue': [(100, 100, 100), (130, 255, 255)],
    }

    results = {}
    for color, (lower, upper) in colors.items():
        mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        ratio = cv2.countNonZero(mask) / mask.size
        results[color] = int(ratio * 100)

    return results
```

**Step 2: Create Feature Wrapper**

```python
# features/color_detection.py

from ai_modules.vision_processor import VisionProcessor

class ColorDetector:
    def __init__(self):
        self.vision = VisionProcessor()

    async def detect_colors_in_scene(self) -> str:
        """Detect and describe colors in current scene."""
        frame = self.vision.capture_image()
        if frame is None:
            return "Could not capture image"

        colors = await self.vision.detect_colors(frame)

        # Generate description
        description = "I see: "
        for color, percentage in colors.items():
            if percentage > 10:
                description += f"{percentage}% {color}, "

        return description.rstrip(', ')
```

**Step 3: Add Intent Mapping**

```python
# ai_modules/llm_handler.py

self.keywords = {
    # ... existing ...
    'detect_colors': ['what colors', 'color palette', 'color scheme'],
}
```

**Step 4: Add Handler in Main App**

```python
# app.py

async def process_command(self, command: str):
    intent = await self.llm.understand_intent(command)

    if intent.get('action') == 'detect_colors':
        await self.detect_colors_in_scene()
    # ... rest of handlers ...

async def detect_colors_in_scene(self):
    self.speech.speak("Analyzing colors")
    try:
        from features.color_detection import ColorDetector
        detector = ColorDetector()
        description = await detector.detect_colors_in_scene()
        self.speech.speak(description)
    except Exception as e:
        logger.error(f"Color detection error: {e}")
        self.speech.speak("Could not analyze colors")
```

**Step 5: Test**

```python
# tests/test_color_detection.py

import pytest
from features.color_detection import ColorDetector

@pytest.mark.asyncio
async def test_color_detection():
    detector = ColorDetector()
    # Requires test image
    # description = await detector.detect_colors_in_scene()
    # assert "colored" in description.lower()
    pass
```

---

### Adding a New Database Model

**Step 1: Define Model**

```python
# database/models.py

class Location(Base):
    __tablename__ = "locations"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String)
    description = Column(String)
    visited_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="locations")
```

**Step 2: Update Handler**

```python
# database/db_handler.py

def save_location(self, user_id: int, lat: float, lon: float, address: str):
    """Save location to history."""
    location = Location(
        user_id=user_id,
        latitude=lat,
        longitude=lon,
        address=address
    )
    self.session.add(location)
    self.session.commit()

def get_location_history(self, user_id: int, limit: int = 10) -> List:
    """Get user's location history."""
    return self.session.query(Location)\
        .filter(Location.user_id == user_id)\
        .order_by(Location.visited_at.desc())\
        .limit(limit)\
        .all()
```

**Step 3: Create Migration** (if using Alembic)

```bash
alembic revision --autogenerate -m "Add Location model"
alembic upgrade head
```

---

### Adding a New Intent

**Step 1: Add Keywords**

```python
# ai_modules/llm_handler.py

self.keywords = {
    'get_time': ['what time', 'tell me time', 'current time'],
    'get_date': ['what date', 'today', 'what day'],
}
```

**Step 2: Implement Handler**

```python
# app.py

async def process_command(self, command: str):
    intent = await self.llm.understand_intent(command)

    if intent.get('action') == 'get_time':
        await self.get_current_time()
    elif intent.get('action') == 'get_date':
        await self.get_current_date()
    # ... rest ...

async def get_current_time(self):
    from datetime import datetime
    current_time = datetime.now().strftime("%I:%M %p")
    self.speech.speak(f"The time is {current_time}")

async def get_current_date(self):
    from datetime import datetime
    current_date = datetime.now().strftime("%A, %B %d, %Y")
    self.speech.speak(f"Today is {current_date}")
```

---

## Code Standards

### Style Guide

**Black Configuration** (`.black`):

```ini
line-length = 100
target-version = ['py38', 'py39', 'py310', 'py311']
```

**Format Code**:

```bash
# Format all files
black .

# Check without formatting
black --check .
```

### Type Hints

```python
from typing import Optional, List, Dict, Tuple, Any, Callable
import numpy as np

# Function signature with type hints
async def process_image(
    self,
    image: np.ndarray,
    confidence: float = 0.5
) -> Dict[str, Any]:
    """Process image and return results.

    Args:
        image: Input image (H×W×3)
        confidence: Detection confidence threshold

    Returns:
        Dictionary with detection results

    Raises:
        ValueError: If image is invalid
    """
    pass

# Class type hints
class VisionProcessor:
    def __init__(self) -> None:
        self.model: Optional[YOLO] = None
        self.cache: Dict[str, Any] = {}
```

### Docstrings

```python
def calculate_iou(box1: Tuple, box2: Tuple) -> float:
    """Calculate Intersection over Union (IoU) between two boxes.

    Args:
        box1: First bounding box (x1, y1, x2, y2)
        box2: Second bounding box (x1, y1, x2, y2)

    Returns:
        IoU score (0-1)

    Raises:
        ValueError: If boxes have invalid format

    Example:
        >>> iou = calculate_iou((0, 0, 10, 10), (5, 5, 15, 15))
        >>> round(iou, 2)
        0.14
    """
    pass
```

### Error Handling

```python
import logging

logger = logging.getLogger(__name__)

async def capture_and_process(self) -> Optional[Dict]:
    """Capture image and detect objects with error handling."""
    try:
        # Likely to fail - validate input
        frame = self.capture_image()
        if frame is None:
            logger.warning("Failed to capture image")
            return None

        # Process
        objects = await self.detect_objects(frame)
        return objects

    except ValueError as e:
        # Known error - log and handle
        logger.error(f"Invalid input: {e}")
        self.speech.speak("Invalid image format")
        return None

    except Exception as e:
        # Unexpected error - log with full context
        logger.exception(f"Unexpected error in image processing: {e}")
        self.speech.speak("System error occurred")
        return None
```

### Async/Await Patterns

```python
# Good - all async operations await properly
async def pipeline(self):
    # Await async functions
    command = await self.speech.listen()
    intent = await self.llm.understand_intent(command)

    # Don't mix sync and async
    frame = self.vision.capture_image()  # Sync - OK
    objects = await self.vision.detect_objects(frame)  # Async - must await

# Bad - forgetting await
async def bad_pipeline(self):
    task = self.speech.listen()  # Forgot await!
    text = task  # Now task is a coroutine, not text
```

---

## Testing

### Unit Tests

```python
# tests/test_vision_processor.py

import pytest
import numpy as np
from ai_modules.vision_processor import VisionProcessor

@pytest.fixture
def vision_processor():
    """Create VisionProcessor instance."""
    return VisionProcessor()

@pytest.fixture
def sample_image():
    """Create sample test image."""
    return np.random.randint(0, 256, (640, 480, 3), dtype=np.uint8)

@pytest.mark.asyncio
async def test_detect_objects(vision_processor, sample_image):
    """Test object detection."""
    objects = await vision_processor.detect_objects(sample_image)

    assert isinstance(objects, list)
    for obj in objects:
        assert 'name' in obj
        assert 'confidence' in obj
        assert 0 <= obj['confidence'] <= 1

def test_capture_image(vision_processor):
    """Test image capture."""
    # May return None if camera unavailable
    frame = vision_processor.capture_image()

    if frame is not None:
        assert frame.ndim == 3
        assert frame.shape[2] == 3  # RGB
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_vision_processor.py

# Run with coverage
pytest --cov=ai_modules --cov-report=html

# Run with verbose output
pytest -v

# Run specific test
pytest tests/test_vision_processor.py::test_detect_objects -v
```

### Integration Tests

```python
# tests/test_integration.py

import pytest
import asyncio
from app import VisionAssistant

@pytest.mark.asyncio
async def test_full_pipeline():
    """Test complete vision assistance pipeline."""
    assistant = VisionAssistant()

    # Simulate: "Describe my surroundings"
    await assistant.describe_environment(detailed=True)

    # Verify no exceptions raised
    # (actual verification would need mocking)
```

---

## Debugging

### Logging Configuration

```python
# app.py or main module

import logging
import logging.handlers

def setup_logging():
    """Configure application logging."""
    logger = logging.getLogger('vision_assistant')
    logger.setLevel(logging.DEBUG)

    # Console handler
    console = logging.StreamHandler()
    console.setLevel(logging.INFO)

    # File handler
    file_handler = logging.handlers.RotatingFileHandler(
        'vision_assistant.log',
        maxBytes=10485760,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    console.setFormatter(formatter)
    file_handler.setFormatter(formatter)

    logger.addHandler(console)
    logger.addHandler(file_handler)

    return logger

logger = setup_logging()
```

### Debug Mode

```python
# app.py

import os

DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

if DEBUG:
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug mode enabled")
```

### Interactive Debugging

```python
# Set breakpoint
import pdb; pdb.set_trace()

# Or use debugger
import ipdb; ipdb.set_trace()

# Python 3.7+
breakpoint()
```

---

## Git Workflow

### Branch Naming

- `feature/feature-name` - New feature
- `bugfix/bug-name` - Bug fix
- `docs/documentation-topic` - Documentation
- `refactor/description` - Code refactoring

### Commit Messages

```
Type: Description (50 chars or less)

Longer description of changes (72 chars per line).

- Bullet point 1
- Bullet point 2

Fixes #123
```

**Types**:

- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation
- `refactor` - Code refactoring
- `perf` - Performance improvement
- `test` - Testing

### Pull Request Checklist

- [ ] Code follows style guide (black, flake8)
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes
- [ ] All tests pass locally
- [ ] Commit messages are clear

---

## Performance Profiling

### CPU Profiling

```python
import cProfile
import pstats
from io import StringIO

def profile_function():
    """Profile vision processing."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Code to profile
    import asyncio
    asyncio.run(process_image())

    profiler.disable()

    # Print results
    stats = pstats.Stats(profiler, stream=StringIO())
    stats.sort_stats('cumulative')
    stats.print_stats(20)
    print(stats.stream.getvalue())
```

### Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile function
python -m memory_profiler vision_processor.py
```

**Mark functions**:

```python
from memory_profiler import profile

@profile
def process_image(image):
    """This function's memory usage will be profiled."""
    pass
```

### Timing Analysis

```python
import time

async def time_operation(name: str, coro):
    """Time how long async operation takes."""
    start = time.time()
    result = await coro
    elapsed = time.time() - start
    print(f"{name} took {elapsed:.2f} seconds")
    return result

# Usage
await time_operation("Object detection", vision.detect_objects(frame))
```

---

## Continuous Integration

### GitHub Actions (Example)

Create `.github/workflows/test.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov black flake8

      - name: Lint with Black
        run: black --check .

      - name: Lint with Flake8
        run: flake8 . --count --select=E9,F63,F7,F82

      - name: Type check with mypy
        run: mypy . --ignore-missing-imports
        continue-on-error: true

      - name: Run tests
        run: pytest --cov=ai_modules --cov=features

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Resources for Developers

- [Python Documentation](https://docs.python.org/3/)
- [AsyncIO Guide](https://docs.python.org/3/library/asyncio.html)
- [SQLAlchemy](https://docs.sqlalchemy.org/21/)
- [PyTorch](https://pytorch.org/docs)
- [YOLOv8](https://docs.ultralytics.com/)
- [OpenCV](https://docs.opencv.org/)
- [Pytest](https://docs.pytest.org/)

---

## See Also

- [ARCHITECTURE.md](../ARCHITECTURE.md) - System design
- [CONTRIBUTING.md](../guidelines/CONTRIBUTING.md) - Contribution guidelines
- [API.md](../API.md) - API reference
- [README.md](/README.md) - Project overview
