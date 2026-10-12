# CONTRIBUTING.md

# Contributing to Vision Assistant

First off, thank you for considering contributing to Vision Assistant! It's people like you that make Vision Assistant such a great tool for accessibility.

## Code of Conduct

We are committed to providing a welcoming and inclusive environment for all contributors. Please read and follow our Code of Conduct:

- Be respectful and professional in all interactions
- Welcome newcomers and help them get started
- Respect differing opinions and experiences
- Focus on constructive feedback
- Report unacceptable behavior to maintainers

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

**How to Submit a Bug Report:**

1. Use a clear and descriptive title
2. Describe the exact steps which reproduce the problem
3. Provide specific examples to demonstrate the steps
4. Describe the behavior you observed after following the steps
5. Explain which behavior you expected to see instead and why
6. Include screenshots if applicable
7. Include your environment details:

```markdown
- **OS**: Windows 11 / macOS 12 / Ubuntu 20.04
- **Python Version**: 3.10.5
- **Application Version**: 1.0.0
- **GPU**: GTX 1060 / CPU Only
- **Error Message**: [Full error message and traceback]
```

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

1. **Use a clear and descriptive title** for the issue
2. **Provide a step-by-step description** of the suggested enhancement
3. **Provide specific examples** to demonstrate the steps
4. **Describe the current behavior** and **expected behavior**
5. **Explain why this enhancement would be useful**
6. **List any similar applications** that have this feature

### Pull Requests

- Fill in the required template
- Follow the Python styleguide
- Include appropriate test cases
- End all files with a newline
- Avoid platform-specific code when possible
- Document public APIs

**Process:**

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Development Setup

### Prerequisites

- Python 3.8+
- Git
- Virtual environment tool (venv, conda, etc.)

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/Khaf-dev/aiforus.git
cd aiforus

# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install development dependencies
pip install -r requirements.txt

# Install development tools
pip install black flake8 mypy pytest

# Copy environment template
cp .env.example .env
```

### Running Tests

```bash
# Run validation tests
python tests/validation.py

# Run feature tests
python test_features.py

# Run unit tests (when available)
pytest tests/

# Check code style
flake8 .

# Format code
black .

# Type checking
mypy .
```

## Styleguide

### Python Styleguide

We follow [PEP 8](https://www.python.org/dev/peps/pep-0008/) with minor modifications:

- Use 4 spaces for indentation
- Maximum line length is 100 characters (except URLs)
- Use meaningful variable names
- Add docstrings to all functions and classes
- Use type hints where possible

**Example:**

```python
from typing import List, Dict, Optional

async def process_command(self, command: str, context: Dict = None) -> Dict:
    """
    Process user voice commands and execute appropriate actions.

    Args:
        command: The voice command string
        context: Optional context dictionary

    Returns:
        Dictionary containing action and parameters
    """
    if context is None:
        context = {}

    # Process command...
    return {
        "action": "action_name",
        "parameters": {}
    }
```

### Commit Messages

- Use the imperative mood ("Add feature" not "Adds feature")
- Limit the first line to 72 characters or less
- Reference issues and pull requests liberally after the first line
- Link to any relevant issues

**Examples:**

```
Add voice feedback to vision features

- Improved user experience with spoken confirmations
- Added status updates for long-running operations
- Fixes #123

Refactor database handler for better error handling

- Centralized error handling
- Improved logging
- Adds proper resource cleanup
- Closes #456
```

### Documentation

- Use clear, accessible language
- Include code examples where helpful
- Update README.md if you change functionality
- Add docstrings to all public functions
- Include type hints in function signatures

**Docstring Example:**

```python
def listen(self, timeout: int = 10) -> Optional[str]:
    """
    Listen for voice input from the user.

    This method records audio from the microphone and converts
    it to text using speech recognition.

    Args:
        timeout: Maximum time to listen in seconds (default: 10)

    Returns:
        Transcribed text, or None if no speech detected

    Raises:
        sr.RequestError: If speech recognition service is unavailable
        sr.UnknownValueError: If speech is not recognizable

    Example:
        >>> engine = SpeechEngine()
        >>> command = await engine.listen()
        >>> print(f"User said: {command}")
    """
```

## Project Structure

```
aiforus/
├── app.py                    # Main application
├── ai_modules/              # Core AI features
│   ├── vision_processor.py
│   ├── speech_engine.py
│   ├── llm_handler.py
│   └── neural_core.py
├── features/                # Feature implementations
│   ├── navigation.py
│   ├── object_detection.py
│   ├── text_reader.py
│   └── face_recognition.py
├── database/               # Database layer
│   ├── models.py
│   └── db_handler.py
├── tests/                  # Test suite
│   ├── validation.py
│   └── __init__.py
├── documentation/          # Documentation
├── requirements.txt        # Dependencies
├── config.yaml            # Configuration
└── .env.example           # Environment template
```

## Areas for Contribution

### High Priority

- [ ] Improve object detection accuracy
- [ ] Add support for additional languages
- [ ] Implement unit tests
- [ ] Improve error handling
- [ ] Add more voice feedback

### Medium Priority

- [ ] Mobile app support
- [ ] Offline mode improvements
- [ ] Performance optimization
- [ ] Additional vision models
- [ ] Database migration scripts

### Low Priority

- [ ] UI dashboard
- [ ] Analytics
- [ ] Extended logging
- [ ] API documentation generation

## Review Process

1. **Code Review**: At least one maintainer will review your pull request
2. **Testing**: Your code must pass all tests
3. **Documentation**: Changes must include documentation updates
4. **Approval**: Maintainers will provide feedback or approval
5. **Merge**: Once approved, your code will be merged

## License

By contributing to Vision Assistant, you agree that your contributions will be licensed under its MIT License.

## Question?

- Create an issue with the `question` label
- Ask in GitHub Discussions
- Email: support@visionassistant.dev

## Resources

- [PEP 8 Style Guide](https://www.python.org/dev/peps/pep-0008/)
- [Python Docstring Conventions](https://www.python.org/dev/peps/pep-0257/)
- [GitHub Flow Guide](https://guides.github.com/introduction/flow/)
- [Semantic Commit Messages](https://seesparkbox.com/foundry/semantic_commit_messages)

Thank you for contributing to Vision Assistant! 🎉

---

Last Updated: February 2026
