import requests
import logging
from typing import Dict, List, Any, Optional
from config import GOOGLE_PLACES_API_KEY

logger = logging.getLogger("restaurant_api")

class RestaurantAPI:
    """
    API client for restaurants
    """
    
    def __init__(self, api_key: str = None):
        """Initialize the API client"""
        self.api_key = api_key or GOOGLE_PLACES_API_KEY
        self.base_url = "https://places.googleapis.com/v1/places:searchNearby"
        
    def geocode_location(self, location: str) -> Optional[str]:
        """
        Convert location name to coordinates
        
        Args:
            location: Location name (e.g., "Paris, France")
            
        Returns:
            Coordinates string in format "lat,lng" or None if not found
        """
        try:
            url = f"{self.base_url}/geocode/json"
            params = {
                "address": location,
                "key": self.api_key
            }
            
            response = requests.get(url, params=params)
            data = response.json()
            
            if data.get("status") == "OK" and data.get("results"):
                location = data["results"][0]["geometry"]["location"]
                return f"{location['lat']},{location['lng']}"
            else:
                logger.error(f"Geocoding failed: {data.get('status')}")
                return None
                
        except Exception as e:
            logger.error(f"Exception in geocode_location: {str(e)}")
            return None
            
    def get_nearby_places(self, location: str, type: str, radius: int = 5000, 
                         keyword: Optional[str] = None) -> Dict[str, Any]:
        """
        Get nearby places from Google Places API
        
        Args:
            location: Coordinates in format "lat,lng"
            type: Place type (e.g., "restaurant")
            radius: Search radius in meters
            keyword: Additional keyword to filter results
            
        Returns:
            API response data
        """
        try:
            url = f"{self.base_url}/nearbysearch/json"
            params = {
                "location": location,
                "type": type,
                "radius": radius,
                "key": self.api_key
            }
            
            if keyword:
                params["keyword"] = keyword
                
            response = requests.get(url, params=params)
            return response.json()
            
        except Exception as e:
            logger.error(f"Exception in get_nearby_places: {str(e)}")
            return {"status": "ERROR", "error": str(e)}
            
    def get_place_details(self, place_id: str) -> Dict[str, Any]:
        """
        Get detailed information about a place
        
        Args:
            place_id: Google Places place_id
            
        Returns:
            API response data
        """
        try:
            url = f"{self.base_url}/details/json"
            params = {
                "place_id": place_id,
                "key": self.api_key
            }
            
            response = requests.get(url, params=params)
            return response.json()
            
        except Exception as e:
            logger.error(f"Exception in get_place_details: {str(e)}")
            return {"status": "ERROR", "error": str(e)}
            
    def format_place_result(self, place: Dict[str, Any]) -> Dict[str, Any]:
        """
        Format a place result into a standardized structure
        
        Args:
            place: Raw place data from API
            
        Returns:
            Formatted place data
        """
        return {
            "name": place.get("name", ""),
            "place_id": place.get("place_id", ""),
            "rating": place.get("rating", 0),
            "user_ratings_total": place.get("user_ratings_total", 0),
            "address": place.get("formatted_address", ""),
            "phone": place.get("formatted_phone_number", ""),
            "website": place.get("website", ""),
            "opening_hours": place.get("opening_hours", {}).get("weekday_text", []),
            "photos": [
                {
                    "height": photo.get("height", 0),
                    "width": photo.get("width", 0),
                    "photo_reference": photo.get("photo_reference", "")
                }
                for photo in place.get("photos", [])[:5]  # Limit to 5 photos
            ]
        }
        
    def search_restaurants(self, location: str, cuisine: Optional[str] = None, 
                         price_level: Optional[int] = None, radius: int = 5000, 
                         limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for restaurants in a location
        
        Args:
            location: Location name (e.g., "Paris, France") or coordinates
            cuisine: Cuisine type to filter by
            price_level: Price level (1-4, where 1 is least expensive)
            radius: Search radius in meters
            limit: Maximum number of results to return
            
        Returns:
            List of restaurants with details
        """
        try:
            # Check if location is coordinates or name
            if "," in location and all(part.replace(".", "", 1).isdigit() for part in location.split(",")):
                # It's coordinates
                coordinates = location
            else:
                # Convert location name to coordinates using geocoding
                coordinates = self.geocode_location(location)
                if not coordinates:
                    logger.error(f"Failed to geocode location: {location}")
                    return []
            
            # Get restaurants
            keyword = cuisine if cuisine else None
            results = self.get_nearby_places(
                location=coordinates,
                type="restaurant",
                radius=radius,
                keyword=keyword
            )
            
            restaurants = []
            
            if results.get("status") == "OK":
                # Apply price level filter if specified
                filtered_results = results.get("results", [])
                if price_level is not None:
                    filtered_results = [r for r in filtered_results if r.get("price_level", 0) == price_level]
                
                for place in filtered_results[:limit]:
                    place_id = place.get("place_id")
                    if place_id:
                        # Get detailed information
                        details = self.get_place_details(place_id)
                        if details.get("status") == "OK":
                            place_details = details.get("result", {})
                            restaurant = self.format_place_result(place_details)
                            
                            # Add restaurant-specific information
                            restaurant["type"] = "restaurant"
                            restaurant["cuisines"] = [t for t in place_details.get("types", []) 
                                                      if t not in ["restaurant", "food", "establishment", "point_of_interest"]]
                            
                            # Extract reviews
                            if place_details.get("reviews"):
                                restaurant["reviews"] = [
                                    {
                                        "author": review.get("author_name", "Anonymous"),
                                        "rating": review.get("rating", 0),
                                        "text": review.get("text", ""),
                                        "time": review.get("time", 0)
                                    }
                                    for review in place_details.get("reviews", [])[:3]  # Limit to 3 reviews
                                ]
                            
                            # Add to list of restaurants
                            restaurants.append(restaurant)
            
            logger.info(f"Found {len(restaurants)} restaurants for {location}")
            return restaurants
                
        except Exception as e:
            logger.error(f"Exception in search_restaurants: {str(e)}")
            return []
            
    def search_restaurants_by_cuisine(self, location: str, cuisines: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for restaurants grouped by cuisine types
        
        Args:
            location: Location name (e.g., "Paris, France")
            cuisines: List of cuisine types to search for
            
        Returns:
            Dict of cuisine types with lists of restaurants
        """
        if not cuisines:
            cuisines = ["italian", "chinese", "japanese", "french", "indian"]
            
        result = {}
        for cuisine in cuisines:
            restaurants = self.search_restaurants(location, cuisine=cuisine, limit=5)
            result[cuisine] = restaurants
            
        return result 