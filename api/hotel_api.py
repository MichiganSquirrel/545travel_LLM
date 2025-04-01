import requests
import logging
import datetime
from typing import Dict, List, Any, Optional
from config import GOOGLE_PLACES_API_KEY

logger = logging.getLogger("hotel_api")

class HotelAPI:
    """
    API client for hotels and accommodations
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
            type: Place type (e.g., "lodging")
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
        
    def search_hotels(self, location: str, check_in: Optional[str] = None, 
                     check_out: Optional[str] = None, type: str = "lodging",
                     keyword: Optional[str] = None, radius: int = 5000,
                     limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for hotels and accommodations in a location
        
        Args:
            location: Location name (e.g., "Paris, France") or coordinates
            check_in: Check-in date in format YYYY-MM-DD (optional)
            check_out: Check-out date in format YYYY-MM-DD (optional)
            type: Accommodation type (default: "lodging")
            keyword: Additional keyword to filter results (e.g., "luxury", "budget")
            radius: Search radius in meters
            limit: Maximum number of results to return
            
        Returns:
            List of hotels with details
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
            
            # Get hotels
            results = self.get_nearby_places(
                location=coordinates,
                type=type,
                radius=radius,
                keyword=keyword
            )
            
            hotels = []
            
            if results.get("status") == "OK":
                for place in results.get("results", [])[:limit]:
                    place_id = place.get("place_id")
                    if place_id:
                        # Get detailed information
                        details = self.get_place_details(place_id)
                        if details.get("status") == "OK":
                            place_details = details.get("result", {})
                            hotel = self.format_place_result(place_details)
                            
                            # Add hotel-specific information
                            hotel["type"] = "hotel"
                            
                            # Add hotel amenities based on types
                            hotel_types = place_details.get("types", [])
                            amenities = []
                            if "spa" in hotel_types or any("spa" in t for t in hotel_types):
                                amenities.append("spa")
                            if "restaurant" in hotel_types:
                                amenities.append("restaurant")
                            if "bar" in hotel_types:
                                amenities.append("bar")
                            if "gym" in hotel_types or "fitness_center" in hotel_types:
                                amenities.append("fitness center")
                            if "swimming_pool" in hotel_types or "pool" in hotel_types:
                                amenities.append("swimming pool")
                                
                            hotel["amenities"] = amenities
                            
                            # Add dummy pricing information (disclaimer)
                            hotel["price_disclaimer"] = "Pricing information not available via Google Places API"
                            
                            if check_in and check_out:
                                try:
                                    # Parse dates
                                    check_in_date = datetime.datetime.strptime(check_in, "%Y-%m-%d")
                                    check_out_date = datetime.datetime.strptime(check_out, "%Y-%m-%d")
                                    
                                    # Calculate number of nights
                                    nights = (check_out_date - check_in_date).days
                                    hotel["requested_stay"] = {
                                        "check_in": check_in,
                                        "check_out": check_out,
                                        "nights": nights
                                    }
                                except Exception as e:
                                    logger.warning(f"Error parsing dates: {str(e)}")
                                    
                            # Extract reviews
                            if place_details.get("reviews"):
                                hotel["reviews"] = [
                                    {
                                        "author": review.get("author_name", "Anonymous"),
                                        "rating": review.get("rating", 0),
                                        "text": review.get("text", ""),
                                        "time": review.get("time", 0)
                                    }
                                    for review in place_details.get("reviews", [])[:3]  # Limit to 3 reviews
                                ]
                            
                            # Add to list of hotels
                            hotels.append(hotel)
            
            logger.info(f"Found {len(hotels)} hotels for {location}")
            return hotels
                
        except Exception as e:
            logger.error(f"Exception in search_hotels: {str(e)}")
            return []
            
    def search_hotels_by_category(self, location: str, categories: List[str] = None) -> Dict[str, List[Dict[str, Any]]]:
        """
        Search for hotels grouped by categories
        
        Args:
            location: Location name (e.g., "Paris, France")
            categories: List of hotel categories to search for
            
        Returns:
            Dict of categories with lists of hotels
        """
        if not categories:
            categories = ["luxury", "budget", "boutique", "resort", "family"]
            
        result = {}
        for category in categories:
            hotels = self.search_hotels(location, keyword=category, limit=5)
            result[category] = hotels
            
        return result 