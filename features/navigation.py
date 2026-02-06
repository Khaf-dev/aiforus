import features
from typing import Dict, List, Tuple
import json
from geopy.geocoders import Nominatim
import geocoder
from math import radians, sin, cos, sqrt, atan2

class NavigationAssistant:
    def __init__(self):
        print("Initializing Navigation Assistant...")
        self.geolocator = Nominatim(user_agent="vision_assistant")
        self.api_keys = self._load_api_keys()
        
    async def get_current_location(self) -> Dict:
        """Get current location using IP of GPS"""
        try:
            # Try to get location from IP
            g = geocoder.ip('me')
            
            if g.ok:
                return {
                    'latitude': g.latlng[0],
                    'longitude': g.latlng[1],
                    'address': g.address,
                    'city': g.city,
                    'country': g.country
                }
                
                # Fallback to GPS (if available)
                # This would require GPS Hardware
                return {
                    'latitude': 0.0,
                    'longitude': 0.0,
                    'address': 'Unknown location',
                }
                
        except Exception as e:
            print(f"Location error: {e}")
            return None
        
        
    async def get_directions(self, start: Dict, destination: str) -> Dict:
        """Get directions to destination"""
        
        # Geocode destination
        dest_location = self.geolocator.geocode(destination)
        
        if not dest_location:
            return {"error": "Destination not found"}
        
        # Use OpenStreetMap or Google Maps API
        directions = await self._get_osm_route(
            (start['latitude'], start['longitude']),
            (dest_location.latitude, dest_location.longitude)
        )
        
        return {
            'destination': destination,
            'distance': directions.get('distance', 'Unknown'),
            'duration': directions.get('duration', 'Unknown'),
            'steps': self._simplify_instructions(directions.get('steps', []))
        }
        
    async def _get_osm_route(self, start: Tuple, end: Tuple) -> Dict:
        """Get route from OpenStreetMap"""
        try:
            url = ""