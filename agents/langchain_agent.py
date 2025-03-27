import json
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
import os
from datetime import datetime

class TravelPlannerAgent:
    def __init__(self):
        self.llm = OpenAI(temperature=0.7)
        self.user_data_file = "user_data.json"
    
    def process_query(self, query_data):
        """Process user query with API data integrations"""
        # Extract user query and API data
        user_query = query_data.get("user_query", {})
        flight_data = query_data.get("flight_data", {})
        hotel_data = query_data.get("hotel_data", {})
        restaurant_data = query_data.get("restaurant_data", {})
        attraction_data = query_data.get("attraction_data", {})
        user_preferences = query_data.get("user_preferences", {})
        
        prompt = PromptTemplate(
            input_variables=[
                "destination", "duration", "budget", "interests", 
                "flight_data", "hotel_data", "restaurant_data", 
                "attraction_data", "user_preferences"
            ],
            template="""
            As a travel planning expert, please generate 3 different travel options for the following travel requirements,
            taking into account the available flight, hotel, restaurant, and attraction data.
            
            Destination: {destination}
            Duration: {duration}
            Budget: {budget}
            Interests: {interests}
            
            Flight information:
            {flight_data}
            
            Hotel options:
            {hotel_data}
            
            Restaurant options:
            {restaurant_data}
            
            Attraction options:
            {attraction_data}
            
            User preferences from past trips:
            {user_preferences}
            
            For each option, please provide:
            1. Option name
            2. Brief description that highlights what makes this option unique
            3. Estimated cost breakdown (flights, accommodations, food, activities)
            4. Main activities tailored to the user's interests
            5. Specific accommodation suggestions from the hotel data
            6. Restaurant recommendations from the restaurant data
            7. Must-see attractions from the attraction data
            
            Return the results in JSON format with an "options" array containing the three options.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        options_json = chain.run(
            destination=user_query.get("destination", "Not specified"),
            duration=user_query.get("duration", "Not specified"),
            budget=user_query.get("budget", "Not specified"),
            interests=user_query.get("interests", "Not specified"),
            flight_data=json.dumps(flight_data),
            hotel_data=json.dumps(hotel_data),
            restaurant_data=json.dumps(restaurant_data),
            attraction_data=json.dumps(attraction_data),
            user_preferences=json.dumps(user_preferences)
        )
        
        try:
            return {"options": json.loads(options_json)}
        except:
            # If the LLM doesn't return valid JSON, handle it simply
            return {"options": {"options": [{"name": "Option parsing error, please try again"}]}}
    
    def generate_detailed_plan(self, query_data, selected_option):
        """Generate detailed travel plan incorporating API data"""
        # Similar implementation as process_query but for detailed plan generation
        # ...

        # For brevity, I'm not including the full implementation here
        pass 