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
    emergency_contact = Column(JSON)
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
                emergency_contact=["+1234567890", "family_member@email.com"]
            )
            self.session.add(default_user)
            self.session.commit()
            
    def get_