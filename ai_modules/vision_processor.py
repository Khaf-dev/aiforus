import cv2
import numpy as np
from ultralytics import YOLO
import easyocr
from transformers import pipeline
import torch
from typing import List, Dict, Any
import asyncio

class VisionProcessor:
    def __init__ (self):
        print("Initializing Vision Processor...")
        
        # Load models
        self.object_model = YOLO('yolov8n.pt') # Lightweight YOLOv8 model
        self.text_reader = easyocr.Reader(['en'])
        self.scene_describer = pipeline(
            "image-to-text",
            model="nlpconnect/vit-gpt2-image-captioning"
        )
        self.face_detector = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        
        # initialize camera
        self.camera = cv2.VideoCapture(0)
        
        # Load known faces (from databases)
        self.known_faces = self._load_known_faces()
        
    def capture_image(self, save_path=None):
        """Capture image from camera"""
        ret, frame = self.camera.read()
        
        if ret and save_path:
            cv2.imwrite(save_path, frame)
            
        return frame if ret else None
    
    async def describe_scene_detailed(self, image):
        """Generate detailed scene description"""
        # Object detection
        objects = self.object_model(image)
        
        # Text extraction
        texts = await self.extract_text(image)
        
        # Scene captioning
        caption = self._generate_caption(image)
        
        # Compose description
        description = f"{caption}. "
        
        if objects:
            obj_list = ', '.join([obj['name']for obj in objects[:5]])
            description += f"I can see {obj_list}. "
            
        if texts:
            description += f"There's text that says: {''.join(texts[:2])}"
            
        return description
    
    async def detect_objects(self, image) -> List[Dict]:
        """Detect objects in image"""
        # Run YOLO detection
        results = self.object_detector(image, verbose=False)[0]
        
        objects = []
        for box in results.boxes:
            obj = {
                'name': self.object_detector.names[int(box.cls[0])],
                'confidence': float(box.conf[0]),
                'bbox': box.xyxy[0].tolist()
            }
            objects.append(obj)
            
        return objects[:10] # return top 10 objects
    
    async def extract_text(self, image) -> List[str]:
        """Extract text from image using OCR"""
        # Convert to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        # Read text
        results = self.text_reader.readtext(rgb_image)
        
        texts = []
        for (bbox, text, prob) in results:
            if prob > 0.5: # confidence threshold
                texts.append(text)
                
        return texts
        
    async def recognized_faces(self, image) -> List[Dict]:
        """REcognize faces in image"""
        # Conver to grayable
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Detect faces
        faces = self.face_detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5
        )
        
        recognized_faces = []
        for (x, y, w, h) in faces:
            # Extract face region
            face_img = image[y:y+h, x:x+w]
            
            ## REcognize (simplified - would integrate with face recognition model)
            # for now, just detect emotions
            emotion = await self.detect_emotions(face_img)
            
            face_info = {
                'bbox': [x, y, w, h],
                'emotion': emotion,
                'name': self._recognize_face(face_img)
            }
            recognized_faces.append(face_info)
        
        return recognized_faces
    
    async def _generate_caption(self, image):
        """Generate image caption"""
        # convert to PIL Image
        from PIL import Image
        pil_image = image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
        
        # Generate caption
        result = self.scene_describer(pil_image)[0]
        return result['generated_text']
    
    async def _detect_emotion(self, face_image):
        """Detect emotion from face"""
        # Simplified - would use emotion detection model
        # For now : return placeholder
        return "neutral"
    
    def _recognize_face(self, face_image):
        """Recognize face from known face"""
        # Would implement face recognition logic
        # For now : return unknown
        return "Unknown"
    
    def _load_known_faces(self):
        """Load known faces from database"""
        # Implementation would load from DB
        return {}
    
    def cleanup(self):
        """Cleanup resources"""
        if self.camera.isOpened():
            self.camera.release()