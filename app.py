import asyncio
import threading
from datetime import datetime
from ai_modules.vision_processor import VisionProcessor
from ai_modules.speech_engine import SpeechEngine
from ai_modules.llm_handler import LLMAssistant
from features.navigation import NavigationAssistant
from database.db_handler import DatabaseHandler
import config

class VisionAssistant:
    def __init__ (self):
        print("Initializing Vision Assistant for Visually impaired...")
        
        
        #Initialize core modules
        self.vision = VisionProcessor()
        self.speech = SpeechEngine()
        self.llm = LLMAssistant()
        self.navigation = NavigationAssistant()
        self.db = DatabaseHandler()
        
        # State management
        self.is_listening = False
        self.is_processing = False
        self.user_context = {}
        
        # Initialize services
        self._setup_services()
        
    def _setup_services(self):
        """Setup all required services"""
        print("Setting up services...")
        
        # Load user preferences
        self.user_context = self.db.get_user_preferences()
        
        # Initialize voice
        self.speech.speak("Vision Assistant initialized. How can I assist you today?")
        
    async def continuous_assistant(self):
        """Main assistant loop"""
        print("Starting continuous assistant mode...")
        
        while True:
            try:
                #Listen for voice command
                command = await self.speech.listen()
                
                if command:
                    await self.process_command(command)
                    
                # Continuous scene description if enabled
                if self.user_context.get('continuous_mode', False):
                    await self.describe_environment()
                    
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error in main loop: {e}")
                self.speech.speak("Sorry, i encountered an error. Please try again.")
                
    async def process_command(self, command: str):
        """Process user voice commands"""
        print(f"Processing command: {command}")
        
        # Process with LLM to understand intent
        intent = await self.llm.understand_intent(command, self.user_context)
        
        # Execute based on intent
        if intent['action'] == 'describe_scene':
            await self.describe_environment(detailed=True)
            
        elif intent['action'] == 'read_text':
            await self.read_text_around()
            
        elif intent['action'] == 'recognize_object':
            await self.identify_objects()
            
        elif intent['action'] == 'navigate':
            await self.assist_navigation(intent['parameters'])

        elif intent['action'] == 'recognize_person':
            await self.recoginize_faces()
            
        elif intent['action'] == 'emergency':
            await self.handle_emergency()
            
        elif intent['action'] == 'general_question':
            response = await self.llm.generate_response(command)
            self.speech.speak(response)
            
    async def describe_environment(self, detailed=False):
        """Describe the current environment"""
        # Capture image
        image = self.vision.capture_image()
        
        # Get description
        if detailed:
            description = await self.vision.describe_scene_detailed(image)
        else:
            description = await self.vision.describe_scene_brief(image)
            
        # Speak description
        self.speech.speak(description)
        
        # Store in context
        self.user_context['last_scene'] = description
        
    async def read_text_around(self):
        """Read any text in th envvironment"""
        image = self.vision.capture_image()
        texts = await self.vision.extract_text(image)
        
        if texts:
            for text in texts:
                self.speech.speak(f"I see text that says: {text}")
        else:
            self.speech.speak("I don't see any readable text around.")
            
    async def identify_objects(self):
        """Identify objects in view"""
        image = self.vision.capture_image()
        objects = await self.vision.detect_objects(image)
        
        if objects:
            object_list = ", ".join([obj['name'] for obj in objects[:5]])
            self.speech.speak(f"I can see: {object_list}")
        else:
            self.speech.speak("I don't detect any objects nearby.")
            
    async def recognize_faces(self):
        """Recognize faces and identify people"""
        image = self.vision.capture_image()
        faces = await self.vision.recognize_faces(image)
        
        if faces:
            for face in faces:
                name = face.get('name', 'Unknown person')
                emotion = face.get('emotion', 'neutral')
                self.speech.speak(f"I see {name} who looks {emotion}")
                
        else:
            self.speech.speak("I don't see any faces")
            
    async def assist_navigation(self, parameters):
        """Assist with navigation"""
        destination = parameters.get('destination')
        
        if destination:
            # Get current location
            location = await self.navigation.get_current_location()
            
            # Get directions
            route = await self.navigation.get_directions(
                location,
                destination
            )
            
            # Speak directions
            for step in route['steps'][:3]: 
                self.speech.speak(step['intruction'])
        
        else:
            self.speech.speak("Please tell me where you want to go.")
            
    async def handle_emergency(self):
        """Handle emergency situations"""
        # Send emergency alert
        await self.db.send_emergency_alert(
            self.user_context.get('emergency_contacts', [])
        )
        
        # Get current location
        location = await self.navigation.get_current_location()
        
        # Speak reassurance
        self.speech.speak(
            f"Emergency alert sent. Your location is {location}. Help is on the way."
        )
        
    def start(self):
        """Start the assistant"""
        print("Starting Vision Assistant...")
        asyncio.run(self.continuous_assistant())
        
    def stop(self):
        """Stop the assistant"""
        print("Stopping Vision Assistant...")
        self.is_listening = False
        
if __name__ == "__main__":
    assistant = VisionAssistant()
    
    try:
        # Start in background thread
        thread = threading.Thread(target=assistant.start)
        thread.daemon = True
        thread.start()
        
        # Keep main thread alive
        while True:
            command = input("Enter 'quit' to stop: ")
            if command.lower() == 'quit':
                assistant.stop()
                break
            
    except KeyboardInterrupt:
        assistant.stop()
        print("\nAssistant stopped. Goodbye!")