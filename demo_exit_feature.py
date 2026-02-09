#!/usr/bin/env python
"""Demo script showing the exit/goodbye feature"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

print("\n" + "="*60)
print("VISION ASSISTANT - EXIT FEATURE DEMO")
print("="*60 + "\n")

print("The Vision Assistant now recognizes these goodbye commands:\n")

goodbye_keywords = [
    "goodbye",
    "bye",
    "exit",
    "quit", 
    "stop",
    "turn off",
    "shut down",
    "close"
]

for i, keyword in enumerate(goodbye_keywords, 1):
    print(f"  {i}. \"{keyword}\"")

print("\n" + "-"*60)
print("You can also say phrases that contain these keywords:\n")

example_phrases = [
    "Goodbye aiforus!",
    "Bye, thank you!",
    "Exit the program",
    "Quit for now",
    "Stop listening",
    "Turn off the assistant",
    "Shut down please",
    "Close the application"
]

for phrase in example_phrases:
    print(f"  • \"{phrase}\"")

print("\n" + "-"*60)
print("\nHOW IT WORKS:")
print("1. Run the application: python app.py")
print("2. Speak any goodbye command like 'goodbye' or 'exit'")
print("3. The app will:")
print("   - Recognize the intent")
print("   - Say: 'Thank you for using Vision Assistant. Goodbye!'")
print("   - Clean up resources (camera, database)")
print("   - Exit gracefully")

print("\n" + "-"*60)
print("\nALTERNATIVE EXIT METHODS:")
print("• Press Ctrl+C in the terminal")
print("• Speak any goodbye phrase (as listed above)")
print("• The app will always clean up properly")

print("\n" + "="*60)
print("Ready to try? Run: python app.py")
print("="*60 + "\n")
