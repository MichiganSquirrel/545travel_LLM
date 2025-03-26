# build a langchain agent which receive json input from userquery.py 
# according to the json input, generate some candidate options for the user to choose from
# based on the user preference, generate the travel plan and save the basic information in the user_data.json file

import json
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from langchain.agents import Tool, AgentExecutor, ZeroShotAgent
import os
from datetime import datetime

# Make sure to set your OpenAI API key
# os.environ["OPENAI_API_KEY"] = "your-api-key"

class TravelPlannerAgent:
    def __init__(self):
        self.llm = OpenAI(temperature=0.7)
        self.user_data_file = "user_data.json"
    
    def load_user_query(self, query_json):
        """Load and parse user query JSON"""
        if isinstance(query_json, str):
            return json.loads(query_json)
        return query_json
    
    def generate_travel_options(self, user_query):
        """Generate travel options based on user query"""
        prompt = PromptTemplate(
            input_variables=["destination", "duration", "budget", "interests"],
            template="""
            As a travel planning expert, please generate 3 different travel options for the following travel requirements:
            
            Destination: {destination}
            Duration: {duration}
            Budget: {budget}
            Interests: {interests}
            
            For each option, please provide:
            1. Option name
            2. Brief description
            3. Estimated cost
            4. Main activities
            5. Accommodation suggestions
            
            Return the results in JSON format.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        options_json = chain.run(
            destination=user_query.get("destination", "Not specified"),
            duration=user_query.get("duration", "Not specified"),
            budget=user_query.get("budget", "Not specified"),
            interests=user_query.get("interests", "Not specified")
        )
        
        try:
            return json.loads(options_json)
        except:
            # If the LLM doesn't return valid JSON, handle it simply
            return {"options": [{"name": "Option parsing error, please try again"}]}
    
    def generate_detailed_plan(self, user_query, selected_option):
        """Generate detailed travel plan based on user's selected option"""
        prompt = PromptTemplate(
            input_variables=["option", "destination", "duration", "interests"],
            template="""
            Based on the following selected travel option and user preferences, generate a detailed itinerary:
            
            Selected option: {option}
            Destination: {destination}
            Duration: {duration}
            Interests: {interests}
            
            Please provide:
            1. Daily itinerary
            2. Recommended restaurants
            3. Transportation suggestions
            4. Must-see attractions
            5. Budget breakdown
            
            Return the results in JSON format.
            """
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        plan_json = chain.run(
            option=selected_option,
            destination=user_query.get("destination", "Not specified"),
            duration=user_query.get("duration", "Not specified"),
            interests=user_query.get("interests", "Not specified")
        )
        
        try:
            return json.loads(plan_json)
        except:
            return {"error": "Plan generation failed, please try again"}
    
    def save_user_data(self, user_query, selected_option, travel_plan):
        """Save user data to JSON file"""
        user_data = {
            "timestamp": datetime.now().isoformat(),
            "user_query": user_query,
            "selected_option": selected_option,
            "travel_plan_summary": {
                "destination": user_query.get("destination"),
                "duration": user_query.get("duration"),
                "budget": user_query.get("budget"),
                "plan_id": f"TP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            }
        }
        
        # Read existing data (if any)
        existing_data = []
        if os.path.exists(self.user_data_file):
            try:
                with open(self.user_data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except:
                existing_data = []
        
        # Add new data and save
        existing_data.append(user_data)
        with open(self.user_data_file, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        
        return user_data["travel_plan_summary"]["plan_id"]
    
    def process_query(self, query_json):
        """Main function to process user query"""
        # Load user query
        user_query = self.load_user_query(query_json)
        
        # Generate travel options
        travel_options = self.generate_travel_options(user_query)
        
        # Return options for user to choose
        return {
            "status": "options_generated",
            "options": travel_options,
            "message": "Please choose one of the following options"
        }
    
    def generate_plan(self, query_json, selected_option_index):
        """Generate travel plan based on user selection"""
        # Load user query
        user_query = self.load_user_query(query_json)
        
        # Regenerate options to get complete data
        travel_options = self.generate_travel_options(user_query)
        
        # Get user selected option
        try:
            selected_option = travel_options["options"][selected_option_index]
        except (IndexError, KeyError):
            return {"status": "error", "message": "Invalid option index"}
        
        # Generate detailed plan
        detailed_plan = self.generate_detailed_plan(user_query, selected_option)
        
        # Save user data
        plan_id = self.save_user_data(user_query, selected_option, detailed_plan)
        
        return {
            "status": "plan_generated",
            "plan_id": plan_id,
            "detailed_plan": detailed_plan,
            "message": "Travel plan has been generated and saved"
        }

# Usage example
if __name__ == "__main__":
    # Sample user query
    sample_query = {
        "destination": "Tokyo",
        "duration": "5 days",
        "budget": "10000 CNY",
        "interests": "Food, Shopping, Cultural experiences"
    }
    
    agent = TravelPlannerAgent()
    
    # Generate options
    options_result = agent.process_query(sample_query)
    print("Generated options:", json.dumps(options_result, ensure_ascii=False, indent=2))
    
    # Assume user selects the first option
    selected_index = 0
    plan_result = agent.generate_plan(sample_query, selected_index)
    print("Generated plan:", json.dumps(plan_result, ensure_ascii=False, indent=2))