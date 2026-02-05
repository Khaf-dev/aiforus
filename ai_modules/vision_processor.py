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
    
    async def detect_object(self, image):
        