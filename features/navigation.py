import requests
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
            url = "http://router.project-osrm.org/route/v1/walking/{},{};{},{}"
            url = url.format(start[1], start[0], end[1], end[0])
            
            response = requests.get(url, params={
                "overview": "false",
                "alternatives": "false",
                "steps": "true"
            })
            
            data = response.json()
            
            if data.get('routes'):
                route = data['routes'][0]
                return {
                    'distance': route['distance'],
                    'duration': route['duration'],
                    'steps': route['legs'][0]['steps']
                }
                
        except Exception as e:
            print(f"Routing error: {e}")
            
        return {}
    
    def _simplify_instructions(self, steps: List) -> List[Dict]:
        """Simplify navigation instructions for speech"""
        simplified = []
        
        for i, step in enumerate(steps[:5]): # Limit to first 5 steps
            instruction = step.get('maneuver', {}).get('instruction', '')
            
            if not instruction:
                # Create simple instruction
                distance = step.get('distance', 0)
                if distance > 0:
                    if distance < 10:
                        instruction = f"Take a few steps"
                    elif distance < 50:
                        instruction = f"Walk about {int(distance)} meters"
                    else:
                        instruction = f"Continue for about {int(distance)} meters"
                        
            simplified.append({
                'instruction': instruction,
                'distance': step.get('distance', 0)
            })
            
        return simplified
    
    async def get_nearby_places(self, category: str, radius: int = 500) -> List[Dict]:
        """Find nearby places of interest"""
        
        # Use Overpass API for OpenStreetMap
        query = f"""
        [out:json];
        (
            node["amenity"="{category}"](around:{radius},{self.current_location[0]},{self.current_location[1]});
            node["shop"="{category}"](around:{radius},{self.current_location[0]},{self.current_location[1]});
        );
        
        out body;
        """
        
        try:
            response = requests.post(
                "https://overpass-api.de/api/interpreter",
                data={'data': query}
            )
            
            places = []
            for element in response.json().get('elements', []):
                places.append({
                    'name': element.get('tags', {}).get('name', 'Unnamed'),
                    'type': category,
                    'distance': self._calculate_distance(
                        (self.current_location[0], self.current_location[1]),
                        (element['lat'], element['lon'])
                    )
                })
                
            return sorted(places, key=lambda x: x['distance'])[:5]
        
        except Exception as e:
            print(f"Nearby places error: {e}")
            return []
        
    def _calculate_distance(self, coord1: Tuple, coord2: Tuple) -> float:
        """Calculate distance between two coordinates in meters"""
        # Haversine formula
        R = 6371000 # Earth radius in meters
        
        lat1, lon1 = radians(coord1[0]), radians(coord1[1])
        lat2, lon2 = radians(coord2[0]), radians(coord2[1])
        
        dlat1 = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat1 / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    async def _send_emergency_alert(self, contacts: List[str]):
        """Send emergency alert to contacts"""
        print(f"Sending emergency alert to: {contacts}")
        
        # This would integrate with SMS/Email APIs
        # For demonstration, just print
        for contact in contacts:
            print(f"Alert sent to {contact}")
            
    def _load_api_keys(self):
        """Load API keys from configuration"""
        # Load from environment or config file
        return {
            'google_maps': None,
            'openweather': None,
            'twilio': None # For SMS alerts
        }