import speech_recognition as sr
import pyttsx3
import asyncio
from gtts import gTTS
import os
import tempfile
from typing import Optional
import threading

class SpeechEngine:
    def __init__(self, language="en"):
        print("Initializing Speech Engine...")
        
        # Initialize TTS engine
        self.tts_engine = pyttsx3.init()
        self.setup_tts()
        
        # initialize STT recognizer
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()
        
        # Configuration
        self.language = language
        self.speech_rate = 150 # words per minute
        
        # Adjust for ambient noise
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            
    def setup_tts(self):
        """Setup TTS Engine properties"""
        voices = self.tts_engine.getProperty("voices")
        
        # Set voice (try: to find natural sounding voice)
        for voice in voices:
            if 'english' in voice.name.lower():
                self.tts_engine.setProperty('voice', voice.id)
                break
            
        # Set rate and volume
        self.tts_engine.setProperty('rate', self.speech_rate)
        self.tts_engine.setProperty('volume', 1.0)
        
    def speak(self, text: str, use_google: bool = False):
        """Convert text to speech"""
        if use_google:
            #Use google tts for better quality (requires internet nantinya)
            tts = gTTS(text=text, lang=self.language, slow=False)
            
            # Save to temp file and play
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
                tts.save(fp.name)
                os.system(f"mpg123 {fp.name}")
                os.unlink(fp.name)
        else:
            # Use offline TTS
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            
    async def listen(self, timeout: int = 5) -> Optional[str]:
        """Listen for speech and convert to text"""
        loop = asyncio.get_event_loop()
        
        try:
            # Run blocking recognition in thread
            text = await loop.run_in_executor(
                None,
                self._recognize_speech,
                timeout
            )
            return text
        
        except Exception as e:
            print(f"Speech recognition error: {e}")
            return None
        
    def _recognize_speech(self, timeout: int) -> Optional[str]:
        """Blocking speech recogntion"""
        with self.microphone as source:
            print("Listening...")
            try:
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=10
                )
                
                # Recognize using google Speech REcogntion
                text = self.recognizer.recognize_google(
                    audio,
                    language=f"{self.language}-{self.language.upper()}"
                )
                
                print(f"Recognized: {text}")
                return text
            
            except sr.WaitTimeoutError:
                return None
            except sr.UnknownValueError:
                print("Could not understand audio")
                return None
            except sr.RequestError as e:
                print(f"Recognition service error: {e}")
                return None
        
    def _set_voice_properties(self, rate=None, volume=None, voice_id=None):
        """Adjust voice properties"""
        if rate:
            self.tts_engine.setProperty('rate', rate)
        if volume:
            self.tts_engine.setProperty('volume', volume)
        if voice_id:
            self.tts_engine.setProperty('voice_id', voice_id)
            
    def stop(self):
        """Stop speech engine"""
        self.tts_engine.stop()