# CI/CD Pipeline Documentation

## Overview

Vision Assistant v1.1 includes a comprehensive GitHub Actions CI/CD pipeline that automatically validates code quality, runs tests, and checks for security vulnerabilities on every push and pull request.

---

## Pipeline Architecture

### Workflow Diagram

```
Push/PR Event
    ↓
┌─────────────────────────────┐
│   Test Job (Matrix)         │
│  - Python 3.9/3.10/3.11     │
│  - Ubuntu Latest            │
└──────────┬──────────────────┘
           ↓
    ┌──────────────────┐
    │ Security Checks  │
    │ - Secret scan    │
    │ - Credential check│
    └────────┬─────────┘
           ↓
┌──────────────────────────────┐
│ Build Notification           │
│ - Final status report        │
│ - Summary generation         │
└──────────────────────────────┘
```

---

## Test Job Details

### Environment Setup

- **Operating System**: Ubuntu Latest (Linux)
- **Python Versions**: 3.9, 3.10, 3.11 (parallel matrix)
- **Cache**: pip packages (10-30% faster builds)

### System Dependencies Installed

```bash
# Audio/Media
libportaudio2           # PyAudio support
libsndfile1            # Sound file handling

# Graphics
libgl1-mesa-glx        # OpenGL support (OpenCV)

# Tools
sudo, apt-get          # Package management
```

### Python Dependencies

**Core Installation:**

- All packages from `requirements.txt`
- torch, transformers, YOLOv8, OpenCV, EasyOCR
- FastAPI, SQLAlchemy, AsyncIO

**Audio Dependencies (Optional):**

- librosa 0.11.0+
- scipy 1.17.0+
- pyaudio (continues if fails)

---

## Validation Stages

### 1. Import Validation

**Purpose**: Verify core dependencies are installable

```python
# Checks these imports
import torch
import cv2
import transformers
import sqlalchemy
```

**Status**: ✓ Pass/✗ Fail (stops pipeline)

### 2. Module Import Validation

**Purpose**: Ensure all project modules load cleanly

```python
from ai_modules.vision_processor import VisionProcessor
from ai_modules.speech_engine import SpeechEngine
from ai_modules.llm_handler import LLMHandler
from ai_modules.sound_localization import SoundLocalizer
from features.navigation import NavigationAssistant
from features.face_recognition import FaceRecognizer
from database.db_handler import DatabaseHandler
```

**Status**: ✓ Pass/✗ Fail (stops pipeline)

### 3. Configuration Validation

**Purpose**: Verify YAML structure and required sections

```yaml
Checks:
✓ config.yaml is valid YAML
✓ Contains [app] section
✓ Contains [speech] section
✓ Contains [ai] section
✓ Contains [vision] section
✓ Contains [sound_localization] section
```

**Status**: ✓ Pass/⚠ Warning (continues)

### 4. Audio Configuration

**Purpose**: Validate sound localization settings

```yaml
sound_localization:
  enabled: true
  detection: { ... }
  localization: { ... }
  obstacles: { ... }
```

**Status**: ⚠ Warning (continues if missing)

### 5. Syntax Compilation

**Purpose**: Python syntax validation

```bash
python -m py_compile app.py
python -m py_compile ai_modules/*.py
python -m py_compile features/*.py
python -m py_compile database/*.py
```

**Status**: ✓ Pass/✗ Fail (stops pipeline)

### 6. Code Quality Linting (flake8)

**Purpose**: Identify code style issues and potential bugs

```bash
# Critical checks (stops on failure)
E9   - Runtime errors
F63  - Invalid format specifier
F7   - Syntax error
F82  - Undefined names

# Warnings (continues)
E    - PEP8 style
W    - PEP8 warnings
C901 - Complexity > 10
```

**Status**: ✓ Pass/⚠ Warning (continues)

### 7. Type Checking (mypy)

**Purpose**: Validate type annotations and catch type errors

```bash
mypy . --ignore-missing-imports
```

**Checks**:

- Type hint correctness
- Function signature compatibility
- Optional/None handling
- Generic type parameters

**Status**: ✓ Pass/⚠ Warning (continues)

---

## Security Job Details

### 1. Secret Scanning

**Purpose**: Detect exposed credentials and API keys

```bash
# Patterns checked
- api_key=...
- password=...
- secret=...
- sk_test/sk_live (Stripe keys)
```

**Status**: ✓ Pass/✗ Fail (stops)

### 2. .env File Verification

**Purpose**: Ensure environment file not committed

```bash
# Checks git history for .env
if [ -f .env ]; then
  if git log --all -- .env | grep -q .; then
    ✗ FAIL: .env found in history
  fi
fi
```

**Status**: ✓ Pass/✗ Fail

---

## Test Results

### Build Matrix Results

Pipeline runs on 3 Python versions in parallel:

```
Python 3.9     ━━━━━━━━━━━━━━━━━ ✓ (2m 30s)
Python 3.10    ━━━━━━━━━━━━━━━━━ ✓ (2m 25s)
Python 3.11    ━━━━━━━━━━━━━━━━━ ✓ (2m 28s)
```

### Summary Report

After completion, GitHub generates:

- ✓ Test results for each Python version
- ✓ Code quality metrics
- ✓ Security scan results
- ✓ Build time and status

---

## Handling Failures

### Type of Failures

#### **Critical (Stops Pipeline)**

- Import errors
- Syntax errors
- Core module load failures
- Secret detection

**Action**: Fix code, commit, push again

#### **Non-Critical (Warnings)**

- Code style (flake8)
- Type hints (mypy)
- Audio configuration missing
- No unit tests found

**Action**: Recommended but not required

### Debug Pipeline Failures

**1. Check logs on GitHub**

```
Actions > [Your Workflow] > [Failed Run] > [Job] > [Step]
```

**2. Run locally to reproduce**

```bash
# Activate venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run imports manually
python -c "from app import VisionAssistant"

# Syntax check
python -m py_compile ai_modules/*.py

# Type check
pip install mypy
mypy . --ignore-missing-imports
```

**3. Common issues**

| Error                         | Cause               | Fix                       |
| ----------------------------- | ------------------- | ------------------------- |
| `ImportError: No module`      | Missing dependency  | Add to requirements.txt   |
| `SyntaxError`                 | Python syntax issue | Check line number in logs |
| `AttributeError: ... unknown` | Type hint missing   | Add type annotations      |
| `Secret detected`             | API key in code     | Move to .env or config    |

---

## Performance Characteristics

### Build Times

- **Quick Run** (cache hit): 1-2 minutes
- **Fresh Install**: 5-8 minutes per Python version
- **Total for 3 versions**: 5-8 minutes (parallel)

### Resource Usage

- **CPU**: Ubuntu-latest (2 cores)
- **Memory**: 7GB available
- **Storage**: 14GB total

### Cache Strategy

```
pip-cache key: os + requirements.txt
Cache path: ~/.cache/pip
Hit rate: 70-80% (subsequent runs)
```

---

## Manual Triggers

### Run Pipeline Manually

1. Go to **Actions** tab on GitHub
2. Select **CI/CD Pipeline**
3. Click **Run workflow**
4. Choose branch (master/main/develop)
5. Click **Run workflow**

### Scheduled Runs (Optional)

To add daily checks, add to workflow:

```yaml
schedule:
  - cron: "0 2 * * *" # 2 AM UTC daily
```

---

## Integration with Branches

### Trigger Rules

- **Branches**: master, main, develop
- **Events**: push, pull_request
- **Auto-run**: Yes (no manual approval needed)

### Branch Protection Rules (Recommended)

Set on GitHub:

```
Settings > Branches > Branch protection rules

✓ Require status checks to pass
✓ Require code reviews (1+)
✓ Dismiss stale reviews
✓ Require branches to be up to date
```

---

## Monitoring & Notifications

### GitHub Status Checks

- ✓ Shows on every merge request
- ✓ Blocks merge if pipeline fails
- ✓ Links to detailed logs

### Email Notifications

GitHub can email on:

- Failed workflows
- Completed workflows
- All events

Enable in: **Settings > Notifications**

---

## Extending the Pipeline

### Add Custom Tests

```yaml
- name: Run custom tests
  run: |
    pip install pytest
    pytest tests/
```

### Add Deployment Step

```yaml
- name: Deploy to production
  if: github.ref == 'refs/heads/master'
  run: |
    # Deploy commands
```

### Add Code Coverage

```yaml
- name: Measure coverage
  run: |
    pip install coverage
    coverage run -m pytest
    coverage report
```

---

## Troubleshooting Pipeline Issues

### "Cannot find module X"

**Cause**: Package not in requirements.txt
**Solution**: Add to requirements.txt and commit

### "Syntax error in app.py"

**Cause**: Invalid Python syntax
**Solution**: Fix syntax, test locally with `python -m py_compile`

### "Secret detected"

**Cause**: Credentials in code
**Solution**: Move to .env, add pattern to .gitignore

### "Type error on line X"

**Cause**: Missing type hints or type mismatch
**Solution**: Add `# type: ignore` or fix type annotations

### "Audio library import failed"

**Cause**: System dependencies missing
**Solution**: These are optional, continue anyway (non-blocking)

---

## Best Practices

1. **Commit frequently** - Catch issues early
2. **Write tests** - Add to tests/ directory
3. **Fix type hints** - Improves code quality
4. **Review logs** - Understand what failed
5. **Branch protect** - Require passing checks before merge
6. **Keep dependencies updated** - Run annually

---

## Migration from Manual Testing

### Before (Manual):

```
1. Developer runs tests locally
2. Pushes code
3. Manual review
4. Merge without verification
```

### After (Automated):

```
1. Push code
2. Pipeline auto-runs on all 3 Python versions
3. Type checking, linting, security scan
4. Results show on PR before merge
5. Merge only after passing all checks
```

---

## Useful Commands for Local Development

```bash
# Run linting locally
pip install flake8
flake8 . --count --exit-zero

# Run type checking
pip install mypy
mypy . --ignore-missing-imports

# Validate config
python -c "import yaml; yaml.safe_load(open('config.yaml'))"

# Test imports
python -c "from app import VisionAssistant; print('✓ OK')"

# Syntax check all files
python -m py_compile app.py ai_modules/*.py features/*.py database/*.py
```
