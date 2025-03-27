import requests
import json
import os
from datetime import datetime

class FlightAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("FLIGHT_API_KEY")
        self.base_url = "https://api.example.com/flights"  # Replace with actual API URL
    
    def search_flights(self, origin, destination, departure_date, return_date=None, adults=1):
        """Search for flights using the API"""
        params = {
            "api_key": self.api_key,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults
        }
        
        if return_date:
            params["return_date"] = return_date
        
        try:
            response = requests.get(self.base_url + "/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_flight_details(self, flight_id):
        """Get detailed information about a specific flight"""
        try:
            response = requests.get(f"{self.base_url}/{flight_id}", params={"api_key": self.api_key})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def load_mock_data(self, file_path):
        """Load mock flight data from a local JSON file (for testing)"""
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load mock data: {str(e)}"} 