"""Vision Assistant - Main Application Entry Point"""
import sys
import os
import asyncio
import logging
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class VisionAssistant:
    """Main Vision Assistant Application"""
    
    def __init__(self):
        """Initialize Vision Assistant"""
        logger.info("Initializing Vision Assistant for Visually Impaired...")
        
        try:
            # Import modules
            from ai_modules.vision_processor import VisionProcessor
            from ai_modules.speech_engine import SpeechEngine
            from ai_modules.llm_handler import LLMHandler
            from features.navigation import NavigationAssistant
            from database.db_handler import DatabaseHandler
            
            # Initialize core modules
            self.vision = VisionProcessor()
            self.speech = SpeechEngine()
            self.llm = LLMHandler()
            self.navigation = NavigationAssistant()
            self.db = DatabaseHandler()
            
            # State management
            self.is_listening = False
            self.is_processing = False
            self.user_context = {}
            
            # Initialize services
            self._setup_services()
            
            logger.info("Vision Assistant initialized successfully!")
            
        except Exception as e:
            logger.error(f"Failed to initialize Vision Assistant: {e}")
            raise
        
    def _setup_services(self):
        """Setup all required services"""
        logger.info("Setting up services...")
        
        try:
            # Load user preferences
            self.user_context = self.db.get_user_preferences()
            
            # Initialize voice
            self.speech.speak("Vision Assistant initialized. How can I assist you today?")
            
            logger.info("Services setup complete!")
            
        except Exception as e:
            logger.warning(f"Warning during service setup: {e}")
        
    async def continuous_assistant(self):
        """Main assistant event loop"""
        logger.info("Starting continuous assistant mode...")
        
        try:
            while True:
                try:
                    # Listen for voice command
                    command = await self.speech.listen()
                    
                    if command:
                        logger.info(f"Command received: {command}")
                        await self.process_command(command)
                    
                    # Continuous scene description if enabled
                    if self.user_context.get('continuous_mode', False):
                        await self.describe_environment()
                    
                    await asyncio.sleep(0.5)
                    
                except KeyboardInterrupt:
                    logger.info("User exit detected. Shutting down...")
                    break
                except Exception as e:
                    logger.error(f"Error in assistant loop: {e}")
        
        except Exception as e:
            logger.error(f"Fatal error in continuous assistance: {e}")
                
    async def process_command(self, command: str):
        """Process user voice commands"""
        logger.info(f"Processing command: {command}")
        
        # Give immediate feedback
        self.speech.speak(f"Processing your request: {command}")
        
        try:
            # Parse intent
            intent = await self.llm.understand_intent(command, self.user_context)
            
            # Give feedback on what will be done
            if intent.get('action') == 'describe_scene':
                self.speech.speak("Analyzing your surroundings...")
                await self.describe_environment(detailed=True)
            
            elif intent.get('action') == 'read_text':
                self.speech.speak("Looking for text in your environment...")
                await self.read_text_around()
            
            elif intent.get('action') == 'recognize_objects':
                self.speech.speak("Identifying objects around you...")
                await self.identify_objects()
            
            elif intent.get('action') == 'navigate':
                self.speech.speak("Getting navigation information...")
                await self.assist_navigation(intent.get('parameters', {}))
            
            elif intent.get('action') == 'recognize_people':
                self.speech.speak("Scanning for faces...")
                await self.recognize_faces()
            
            elif intent.get('action') == 'emergency':
                self.speech.speak("Activating emergency alert...")
                await self.handle_emergency()
            
            elif intent.get('action') == 'exit':
                await self.handle_exit()
                raise KeyboardInterrupt("User requested exit")
            
            elif intent.get('action') == 'general_question':
                response = await self.llm.generate_response(command)
                self.speech.speak(response)
            
            else:
                self.speech.speak("I didn't quite understand that. Could you repeat?")
        
        except KeyboardInterrupt:
            raise
        except Exception as e:
            logger.error(f"Error processing command: {e}")
            self.speech.speak("I encountered an error processing your request. Please try again.")
            
    async def describe_environment(self, detailed=False):
        """Describe the current environment"""
        try:
            # Capture image from camera
            image = self.vision.capture_image()
            
            if image is not None:
                # Provide feedback that processing is happening
                if detailed:
                    self.speech.speak("Analyzing scene in detail...")
                else:
                    self.speech.speak("Scanning environment...")
                
                # Get description
                if detailed:
                    description = await self.vision.describe_scene_detailed(image)
                else:
                    description = await self.vision.describe_scene_brief(image)
                
                # Speak description
                if description:
                    self.speech.speak(description)
                    logger.info(f"Scene: {description}")
                else:
                    self.speech.speak("Unable to analyze scene at this moment.")
                
                # Store in context
                self.user_context['last_scene'] = description
            else:
                self.speech.speak("Camera is not available. Please check your camera connection.")
                logger.warning("No camera feed available")
        
        except Exception as e:
            logger.error(f"Error describing environment: {e}")
            self.speech.speak("I encountered an error analyzing the scene.")
        
    async def read_text_around(self):
        """Read any text in the environment"""
        try:
            image = self.vision.capture_image()
            if image is not None:
                self.speech.speak("Scanning for text...")
                texts = await self.vision.extract_text(image)
                
                if texts:
                    self.speech.speak(f"I found {len(texts)} text regions. Reading them now.")
                    for i, text in enumerate(texts[:5], 1):
                        self.speech.speak(f"Text {i}: {text}")
                        logger.info(f"Extracted text {i}: {text}")
                else:
                    self.speech.speak("I don't see any readable text around you.")
            else:
                self.speech.speak("Camera not available for text reading.")
        except Exception as e:
            logger.error(f"Error reading text: {e}")
            self.speech.speak("I couldn't read text from the scene.")
            
    async def identify_objects(self):
        """Identify objects in view"""
        try:
            image = self.vision.capture_image()
            if image is not None:
                self.speech.speak("Identifying objects in your surroundings...")
                objects = await self.vision.detect_objects(image)
                
                if objects:
                    object_list = ", ".join([obj.get('name', 'Unknown') for obj in objects[:5]])
                    self.speech.speak(f"I can see the following objects: {object_list}")
                    logger.info(f"Detected objects: {object_list}")
                else:
                    self.speech.speak("I don't detect any specific objects nearby.")
            else:
                self.speech.speak("Camera not available for object detection.")
        except Exception as e:
            logger.error(f"Error identifying objects: {e}")
            self.speech.speak("I couldn't identify objects in the scene.")
            
    async def recognize_faces(self):
        """Recognize faces and identify people"""
        try:
            image = self.vision.capture_image()
            if image is not None:
                self.speech.speak("Scanning for faces...")
                faces = await self.vision.recognize_faces(image)
                
                if faces:
                    face_count = len(faces)
                    self.speech.speak(f"I detected {face_count} face{'' if face_count == 1 else 's'} nearby.")
                    for i, face in enumerate(faces, 1):
                        name = face.get('name', 'Unknown person')
                        self.speech.speak(f"Face {i}: {name}")
                    logger.info(f"Found {face_count} faces")
                else:
                    self.speech.speak("I don't see any faces around you.")
            else:
                self.speech.speak("Camera not available for face recognition.")
        except Exception as e:
            logger.error(f"Error recognizing faces: {e}")
            self.speech.speak("I couldn't detect faces in the scene.")
            
    async def assist_navigation(self, parameters):
        """Assist with navigation"""
        try:
            destination = parameters.get('destination')
            
            if destination:
                self.speech.speak(f"Getting directions to {destination}...")
                
                # Get current location
                location = await self.navigation.get_current_location()
                if location:
                    self.speech.speak(f"Your current location is {location}")
                
                # Get directions
                route = await self.navigation.get_directions(
                    location,
                    destination
                )
                
                # Speak directions
                if route and 'steps' in route:
                    self.speech.speak(f"I found a route to {destination}. Here are the first few directions.")
                    for step in route['steps'][:3]:
                        instruction = step.get('instruction', '')
                        if instruction:
                            self.speech.speak(instruction)
                            logger.info(f"Direction: {instruction}")
                else:
                    self.speech.speak(f"I couldn't find directions to {destination}.")
            else:
                self.speech.speak("Please tell me where you want to go.")
        except Exception as e:
            logger.error(f"Error navigating: {e}")
            self.speech.speak("I encountered an error during navigation.")
            
    async def handle_emergency(self):
        """Handle emergency situations"""
        try:
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
        except Exception as e:
            logger.error(f"Error handling emergency: {e}")
    
    async def handle_exit(self):
        """Handle user exit/goodbye command"""
        try:
            logger.info("User requested exit")
            
            # Provide farewell message
            self.speech.speak("Thank you for using Vision Assistant. Goodbye!")
            
            # Cleanup resources
            self.vision.cleanup()
            self.db.close()
            
            logger.info("Vision Assistant stopped gracefully")
        
        except Exception as e:
            logger.error(f"Error during exit: {e}")
            self.speech.speak("Shutting down. Goodbye!")
    
    def stop(self):
        """Stop the assistant"""
        logger.info("Stopping Vision Assistant...")
        self.is_listening = False


async def main():
    """Main entry point"""
    try:
        assistant = VisionAssistant()
        
        # Check for command-line arguments
        if len(sys.argv) > 1:
            if sys.argv[1] == '--test':
                logger.info("Running in test mode...")
                # Test a simple command
                await assistant.process_command("describe the scene")
                return True
            elif sys.argv[1] == '--test-import':
                logger.info("Import test passed!")
                return True
            elif sys.argv[1] == '--debug':
                logger.info("Debug mode enabled")
        
        # Run continuous assistance
        await assistant.continuous_assistant()
        
    except KeyboardInterrupt:
        logger.info("Shutting down Vision Assistant...")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return False
    
    return True


if __name__ == "__main__":
    # For Python 3.13, use asyncio.run()
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        sys.exit(1)