from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import json
import os


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String)
    disability_type = Column(String)
    preferences = Column(JSON) # Store user preferences as JSON
    emergency_contacts = Column(JSON)
    created_at = Column(DateTime, default=datetime.timezone.utcnow)
    
class ConversationHistory(Base):
    __tablename__ = 'conversations'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer)
    user_input = Column(String)
    assistant_response = Column(String)
    timestamp = Column(DateTime, default=datetime.timezone.utcnow)
    
class DatabaseHandler():
    def __init__(self, db_path='vision_assistant.db'):
        print("Initializing Database Handler...")
        
        self.engine = create_engine(f"sqlite:///{db_path}")
        Base.metadata.create_all(self.engine)
        
        Session = sessionmaker(bind=self.engine)
        self.session = Session()
        
        # Create default user if not exists
        self._create_default_user()
        
    def _create_default_user(self):
        """Create default user profile"""
        user = self.session.query(User).first()
        
        if not user:
            default_user = User(
                name="Default user",
                disability_type="visually_impaired",
                preferences={
                    "voice_speed": 150,
                    "voice_type": "female",
                    "continuous_mode": False,
                    "detail_level": "normal",
                    "language": "en"
                },
                emergency_contacts=["+1234567890", "family_member@email.com"]
            )
            self.session.add(default_user)
            self.session.commit()
            
    def get_user_preferences(self, user_id=1) -> dict:
        """Get user preferences"""
        user = self.session.query(User).filter_by(id=user_id).first()
        
        if user:
            return {
                **user.preferences,
                "emergency_contacts": user.emergency_contacts,
                "disability_type": user.disability_type
            }
        return {}
    
    def update_user_preferences(self, preferences: dict, user_id=1):
        """Update user preferences"""
        user = self.session.query(User).filter_by(id=user_id).first()
        
        if user:
            user.preferences = {**user.preferences, **preferences}
            self.session.commit()
            
    def save_scene_memory(self, user_id: int, location: str,
                          description: str, objects: list):
        """Save scene description to memory"""
        memory = SceneMemory(
            user_id=user_id,
            location=location,
            description=description,
            objects_detected=objects
        )
        self.session.add(memory)
        self.session.commit()
        
    def get_location_history(self, user_id: int, limit: int = 10) -> list:
        """Get location history"""
        memories = self.session.query(SceneMemory)\
            .filter_by(user_id=user_id)\
                .order_by(SceneMemory.timestamp.desc())\
                    .limit(limit)\
                        .all()
                        
        return [
            {
                'location': m.location,
                'description': m.description,
                'timestamp': m.timestamp.isoformat()
            }
            for m in memories
        ]
        
    def save_conversation(self, user_id: int,
                          user_input: str,
                          assistant_response: str):
        """Save conversation to history"""
        conversation = ConversationHistory(
            user_id=user_id,
            user_input=user_input,
            assistant_response=assistant_response
        )
        self.session.add(conversation)
        self.session.commit()
        
    def get_conversation_history(self, user_id: int, limit: int = 20) -> list:
        """Get conversation history"""
        conversations = self.session.query(ConversationHistory)\
            .filter_by(user_id=user_id)\
                .order_by(ConversationHistory.timestamp.desc())\
                    .limit(limit)\
                        .all()
                        
        return [
            {
                'user_input': c.user_input,
                'assistant': c.assistant_response,
                'timestamp': c.timestamp.isoformat()
            }
            for c in conversations
        ]
        
    def add_known_face(self, user_id: int, name: str, face_data: dict):
        """Add known face to database"""
        # This would store face embeddings
        # For now, implement as needed
        pass
    
    def get_known_faces(self, user_id: int) -> list:
        """Get known faces for user"""
        # Retrieve from database
        return []
    
    def close(self):
        """Close database connection"""
        self.session.close()