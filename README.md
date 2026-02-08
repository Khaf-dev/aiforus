# Vision Assistant for Visually Impaired (Development Stage)

![Python](https://img.shields.io/badge/Python-3.8%2B-blue)
![AI](https://img.shields.io/badge/AI-Computer%20Vision-green)
![Accessibility](https://img.shields.io/badge/Accessibility-For%20Visually%20Impaired-orange)

An AI-Powered assistant that helps visually impaired people "see" their environment through computer vision, voice interaction, and intelligent scene description.

## Features

### AI-Powered Vision

- **Real-Time Object Detection** (YOLOv8)
- **Text Reading** (OCR with EasyOCR)
- **Scene Description** (Image Captioning)
- **Face Recognition** (Basic Implementation)
- **Environment Understanding** (LLM Integration)

### Voice Interaction

- **Speech-to-Text** (Google/Offline recognition)
- **Text-to-Speech** (Natural voice output)
- **Voice Commands** (Natural Language Processing)
- **Conversational AI** (Context-aware Responses)

### Navigation Assistance

- **Voice-first Interface** (No visual AI required)
- **Customization preferences** (Voice speed, detail level)
- **User memory** (Remembers preferences and faces)
- **Offline capable** (Works without internet)

## Quick Start

### Prerequisites

- Python 3.8 or higher
- Camera (webcam or external)
- Microphone and Speakers
- 4GB+ RAM (8GB recommended)

### Installation

```bash
# Clone the repository
git clone https://github.com/khaf-dev/aiforus.git
cd aiforus

```

# Automatic setup (recommended)

```bash
python deploy.py

```

# Or manual setup

```bash
python -m venv venv

```

# Activate virtual environment

## Windows:

```bash

venv\Scripts\activate

```

## Linux/Mac:

```bash

source venv/bin/activate

```

## Install dependencies

```bash

pip install -r requirements.txt

```

# Configuration

1. **Edit .env file with your API keys (Development Stage for testing)**

```bash
OPENAI_API_KEY=your_api_key_here
GOOGLE_MAPS_API_KEY=your_api_key_here
WEATHER_API_KEY=your_api_key_here

```

2. **Adjust setting in config.yaml if needed**

## Usage

```bash
# Start the assistant
python app.py

# Or use the provided scripts
# Windows: run.bat
# Linux/Mac: ./run.sh

```

# Voice Commands

## Try saying:

- "What's in front of me?" - Scene description
- "Read the text around" - OCR text reading
- "Take me to [destination]" - Navigation
- "Who is this person?" - Face recognition
- "Help, emergency!" - Emergency mode
- "What's the weather?" - General questions

# Vision Assistant Roadmap

## Phase 1: MVP (Complete)

- [x] Basic object detection
- [x] Text reading (OCR)
- [x] Voice interactions
- [x] Navigation assistance
- [x] User preferences
- [x] Documentation

## Phase 2: Enchancement (Current)

### Q1 2026

- [] Advanced face recognition
- [] Indoor navigation (SLAM)
- [] Indonesian language support
- [] Mobile App prototype
- [] Performance optimization

### Q2 2026

- [] Real-time obstacle detection
- [] Color identification
- [] Currency recognition
- [] Medication identification
- [] Cloud sync for preferences

## Phase 3: Advanced features

### Q3 2026

- [] AR Glasses integration
- [] Social features (connect with volunteers)
- [] Educational mode (learn objects)
- [] Multi-user support
- [] Advanced AI models

### Q4 2026

- [] Real-Time translation
- [] Emotion recognition
- [] Predictive assistance
- [] Hardware integrations
- [] App Store deployment

## Technical Debt & Improvements

- [] Codebase refactoring
- [] Test coverage improvement
- [] Documentation expansion
- [] Performance benchmarking
- [] Security audit

## Community & Outreach

- [] User testing program
- [] Accessibility certification
- [] Partnership with disability organizations
- [] Hackathons & workshops
- [] Research publications
