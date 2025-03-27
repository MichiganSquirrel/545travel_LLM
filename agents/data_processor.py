import json
import os
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class DataProcessor:
    def __init__(self):
        self.llm = OpenAI(temperature=0.3)
        self.template_dir = "templates/data_processing"
    
    def process_api_data(self, data_type, api_data):
        """Process and summarize API data based on its type"""
        template_path = os.path.join(self.template_dir, f"{data_type}_template.txt")
        
        if not os.path.exists(template_path):
            return {
                "error": f"Template for {data_type} not found",
                "raw_data": api_data
            }
        
        # Load the appropriate template
        with open(template_path, "r") as f:
            template = f.read()
        
        prompt = PromptTemplate(
            input_variables=["api_data"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Convert API data to string if it's a dict
        if isinstance(api_data, dict):
            api_data_str = json.dumps(api_data)
        else:
            api_data_str = str(api_data)
        
        # Generate summary
        try:
            summary_json = chain.run(api_data=api_data_str)
            return json.loads(summary_json)
        except Exception as e:
            # Fallback if processing fails
            return {
                "error": f"Failed to process {data_type} data: {str(e)}",
                "raw_data": api_data
            }
    
    def process_flight_data(self, flight_data):
        """Process flight API data"""
        return self.process_api_data("flight", flight_data)
    
    def process_hotel_data(self, hotel_data):
        """Process hotel API data"""
        return self.process_api_data("hotel", hotel_data)
    
    def process_restaurant_data(self, restaurant_data):
        """Process restaurant API data"""
        return self.process_api_data("restaurant", restaurant_data)
    
    def process_attraction_data(self, attraction_data):
        """Process attraction API data"""
        return self.process_api_data("attraction", attraction_data) 