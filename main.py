import os
from agents.langchain_agent import TravelPlannerAgent
from agents.data_processor import DataProcessor
from api.flight_api import FlightAPI
from api.hotel_api import HotelAPI
from api.restaurant_api import RestaurantAPI
from api.attraction_api import AttractionAPI

class TravelRecommendationSystem:
    def __init__(self):
        # Initialize components
        self.travel_agent = TravelPlannerAgent()
        self.data_processor = DataProcessor()
        
        # Initialize API clients
        self.flight_api = FlightAPI()
        self.hotel_api = HotelAPI()
        self.restaurant_api = RestaurantAPI()
        self.attraction_api = AttractionAPI()
    
    def process_travel_query(self, user_query):
        """Process user's travel query"""
        try:
            # Fetch data from APIs
            flight_data = self.flight_api.search_flights(
                origin=user_query.get('origin'),
                destination=user_query.get('destination'),
                departure_date=user_query.get('departure_date'),
                return_date=user_query.get('return_date')
            )
            
            hotel_data = self.hotel_api.search_hotels(
                location=user_query.get('destination'),
                check_in=user_query.get('departure_date'),
                check_out=user_query.get('return_date')
            )
            
            restaurant_data = self.restaurant_api.search_restaurants(
                location=user_query.get('destination')
            )
            
            attraction_data = self.attraction_api.search_attractions(
                location=user_query.get('destination')
            )
            
            # Process API data
            processed_data = {
                "flight_data": self.data_processor.process_flight_data(flight_data),
                "hotel_data": self.data_processor.process_hotel_data(hotel_data),
                "restaurant_data": self.data_processor.process_restaurant_data(restaurant_data),
                "attraction_data": self.data_processor.process_attraction_data(attraction_data),
                "user_query": user_query
            }
            
            # Generate travel recommendations
            recommendations = self.travel_agent.process_query(processed_data)
            
            return {
                "status": "success",
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def generate_detailed_plan(self, user_query, selected_option):
        """Generate detailed plan based on user's selected option"""
        try:
            return self.travel_agent.generate_detailed_plan(user_query, selected_option)
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error generating detailed plan: {str(e)}"
            }

def main():
    # Create system instance
    system = TravelRecommendationSystem()
    
    # Sample query
    sample_query = {
        "origin": "Beijing",
        "destination": "Shanghai",
        "departure_date": "2024-04-01",
        "return_date": "2024-04-05",
        "budget": "medium",
        "interests": ["culture", "food", "shopping"]
    }
    
    # Process query
    result = system.process_travel_query(sample_query)
    
    # Print results
    if result["status"] == "success":
        print("Recommendations:")
        print(result["recommendations"])
    else:
        print("Error:", result["message"])

if __name__ == "__main__":
    main() 