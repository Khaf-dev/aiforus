#!/usr/bin/env python
"""Test script to verify camera and vision features"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

import cv2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_camera():
    """Test if camera is working"""
    print("\n" + "="*60)
    print("TESTING CAMERA")
    print("="*60)
    
    try:
        camera = cv2.VideoCapture(0)
        
        if not camera.isOpened():
            print("❌ Camera not available")
            print("   - Check if camera is connected")
            print("   - Check camera permissions")
            return False
        
        print("✓ Camera is available")
        
        # Try to capture a frame
        ret, frame = camera.read()
        
        if not ret:
            print("❌ Could not capture frame from camera")
            camera.release()
            return False
        
        print("✓ Successfully captured a frame")
        frame_info = f"Frame size: {frame.shape[0]}x{frame.shape[1]} pixels"
        print(f"✓ {frame_info}")
        
        camera.release()
        return True
    
    except Exception as e:
        print(f"❌ Error testing camera: {e}")
        return False


def test_vision_models():
    """Test if vision models are available"""
    print("\n" + "="*60)
    print("TESTING VISION MODELS")
    print("="*60)
    
    try:
        from ai_modules.vision_processor import VisionProcessor
        
        print("Initializing VisionProcessor...")
        vp = VisionProcessor()
        print("✓ VisionProcessor initialized")
        
        # Try to detect objects in a dummy frame
        import numpy as np
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        print("Testing object detection...")
        import asyncio
        objects = asyncio.run(vp.detect_objects(dummy_frame))
        print(f"✓ Object detection ready (would detect from real images)")
        
        print("Testing text extraction...")
        texts = asyncio.run(vp.extract_text(dummy_frame))
        print("✓ Text extraction ready (would extract from real images)")
        
        print("Testing face detection...")
        faces = asyncio.run(vp.recognize_faces(dummy_frame))
        print("✓ Face detection ready (would detect from real images)")
        
        return True
    
    except Exception as e:
        print(f"❌ Error testing vision models: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_speech():
    """Test if speech engine is working"""
    print("\n" + "="*60)
    print("TESTING SPEECH ENGINE")
    print("="*60)
    
    try:
        from ai_modules.speech_engine import SpeechEngine
        
        print("Initializing SpeechEngine...")
        se = SpeechEngine()
        print("✓ SpeechEngine initialized")
        
        print("Testing text-to-speech...")
        se.speak("Hello! Vision Assistant is working correctly.")
        print("✓ Text-to-speech working")
        
        return True
    
    except Exception as e:
        print(f"❌ Error testing speech: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("VISION ASSISTANT - FEATURE TEST")
    print("="*60)
    
    results = {
        'Camera': test_camera(),
        'Vision Models': test_vision_models(),
        'Speech Engine': test_speech(),
    }
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    for feature, status in results.items():
        status_text = "✓ PASS" if status else "❌ FAIL"
        print(f"{feature:.<30} {status_text}")
    
    all_passed = all(results.values())
    
    print("\n" + "="*60)
    if all_passed:
        print("ALL TESTS PASSED! ✓")
        print("\nYour Vision Assistant is ready to use:")
        print("1. Run: python app.py")
        print("2. Speak commands to interact with the assistant")
        print("3. The app will respond with voice feedback")
    else:
        print("Some tests failed. Please check the errors above.")
        if not results['Camera']:
            print("\nCamera issue detected:")
            print("- Make sure your camera is connected")
            print("- Check camera permissions")
            print("- If using remote desktop, camera forwarding may be needed")
    print("="*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\nFatal error: {e}")
        sys.exit(1)
