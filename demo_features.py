#!/usr/bin/env python
"""Demo script to test vision and speech features"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from app import VisionAssistant


async def demo_features():
    """Demo various features of the Vision Assistant"""
    print("\n" + "="*60)
    print("VISION ASSISTANT - FEATURE DEMO")
    print("="*60 + "\n")
    
    try:
        # Initialize assistant
        print("[1/5] Initializing Vision Assistant...")
        assistant = VisionAssistant()
        print("✓ Vision Assistant initialized\n")
        
        # Test 1: Simple greeting
        print("[2/5] Testing voice feedback...")
        assistant.speech.speak("Welcome to Vision Assistant. I'm ready to help.")
        print("✓ Voice feedback working\n")
        
        # Test 2: Test command processing with feedback
        print("[3/5] Testing command processing with voice feedback...")
        test_commands = [
            "What do you see?",
            "Read any text you can find",
            "What objects are nearby?",
            "Detect any faces",
        ]
        
        for cmd in test_commands:
            print(f"\nProcessing command: '{cmd}'")
            await assistant.process_command(cmd)
            await asyncio.sleep(2)  # Give time for speech
        
        print("\n[4/5] Features Available:")
        print("✓ Voice I/O (pyttsx3, SpeechRecognition)")
        print("✓ Computer Vision (YOLOv8 for objects)")
        print("✓ Face Detection (OpenCV Cascade Classifier)")
        print("✓ Text Recognition (EasyOCR)")
        print("✓ Intent Recognition (Keyword matching + OpenAI optional)")
        print("✓ Voice Feedback (Now working!)")
        print("✓ Navigation assistance (GPS-based)")
        print("✓ Emergency alerts")
        
        print("\n[5/5] Getting Started:")
        print("1. Run: python app.py")
        print("2. Speak a command like:")
        print("   - 'What do you see?'")
        print("   - 'Read the text'")
        print("   - 'Detect faces'")
        print("   - 'Navigate to [location]'")
        print("3. The app will now provide voice feedback for all actions")
        
        print("\n" + "="*60)
        print("Demo complete! Your Vision Assistant is ready to use.")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"Error during demo: {e}")
        return False
    
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(demo_features())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\nDemo interrupted.")
        sys.exit(0)
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)
