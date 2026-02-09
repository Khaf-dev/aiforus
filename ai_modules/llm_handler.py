from openai import OpenAI
from typing import Dict, List, Any
import json
import torch
from transformers import AutoModelForCausalLM, pipeline, AutoTokenizer
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

class LLMHandler:
    """Language Model Handler for intent recognition and responses"""
    
    def __init__(self, use_openai: bool = True):
        """Initialize LLM Handler"""
        logger.info("Initializing LLM Handler...")
        
        self.use_openai = use_openai
        self.model = None
        self.client = None
        
        if use_openai:
            # Initialize OpenAI client with API key from environment
            api_key = os.getenv("OPENAI_API_KEY", "")
            if api_key:
                self.client = OpenAI(api_key=api_key)
                self.model = "gpt-3.5-turbo"
                logger.info("Using OpenAI for LLM")
            else:
                logger.warning("OpenAI API key not found, falling back to local model")
                self.use_openai = False
        else:
            logger.info("Using local model for LLM")
        
        # Conversation history
        self.conversation_history = []
        
        # Predefined intents
        self.intents = {
            'describe_scene': ['describe', 'what do you see', 'what around'],
            'read_text': ['read', 'what does it say', 'text'],
            'recognize_objects': ['objects', 'what things', 'identify'],
            'navigate': ['go to', 'navigate', 'directions to', 'how to get to'],
            'recognize_people': ['who is this', 'identify person', 'do you know this person'],
            'emergency': ['help', 'emergency', 'danger', 'call for help'],
            'exit': ['goodbye', 'bye', 'exit', 'quit', 'stop', 'turn off', 'shut down', 'close'],
            'general_questions': ['what', 'how', 'why', 'when', 'where']
        }
        
    
    async def understand_intent(self, command: str, context: Dict = None) -> Dict:
        """Understand user intent from command"""
        if context is None:
            context = {}
        
        try:
            if self.use_openai and self.client and self.model:
                # Use GPT for intent recognition
                prompt = f"""
                User command: {command}
                
                Classify the intent and extract parameters.
                Intent options: {', '.join(self.intents.keys())}
                
                Return JSON format: {{"action": "action_name", "parameters": {{}}}}
                """
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=100
                )
                
                result = json.loads(response.choices[0].message.content)
                return result
            
            else:
                # Use keyword matching for local intent recognition
                for intent, keywords in self.intents.items():
                    for keyword in keywords:
                        if keyword.lower() in command.lower():
                            return {
                                "action": intent,
                                "parameters": {"query": command}
                            }
                
                return {
                    "action": "general_questions",
                    "parameters": {"query": command}
                }
        
        except Exception as e:
            logger.error(f"Error understanding intent: {e}")
            return {
                "action": "general_questions",
                "parameters": {"query": command}
            }
    
    async def generate_response(self, query: str, context: Dict = None) -> str:
        """Generate natural language response"""
        if context is None:
            context = {}
        
        try:
            if self.use_openai and self.client and self.model:
                messages = [
                    {"role": "system", "content": "You are a helpful assistant for visually impaired people."},
                    {"role": "user", "content": query}
                ]
                
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=200
                )
                
                return response.choices[0].message.content
            
            else:
                # Local model response
                return f"Understood: {query}."
        
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I encountered an error processing your request."
    
    async def generate_scene_description(self, objects: List = None, texts: List = None, context: Dict = None) -> str:
        """Generate scene natural description"""
        if objects is None:
            objects = []
        if texts is None:
            texts = []
        if context is None:
            context = {}
        
        description = "Here's what I can describe: "
        
        if objects:
            description += f"I see {', '.join(objects)}. "
        
        if texts:
            description += f"I found text: {', '.join(texts)}. "
        
        if not objects and not texts:
            description += "I don't detect any notable objects or text in the current scene."
        
        return description