import json
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class FlightProcessor:
    def __init__(self):
        self.llm = OpenAI(temperature=0.3)
        
    def process_flight_data(self, flight_data):
        """Process and summarize flight data"""
        
        # Load the flight summary template
        with open("templates/flight_summary.txt", "r") as f:
            template = f.read()
        
        prompt = PromptTemplate(
            input_variables=["flight_data"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Convert flight data to string if it's a dict
        if isinstance(flight_data, dict):
            flight_data_str = json.dumps(flight_data)
        else:
            flight_data_str = str(flight_data)
        
        # Generate summary
        summary_json = chain.run(flight_data=flight_data_str)
        
        try:
            return json.loads(summary_json)
        except:
            # Fallback if JSON parsing fails
            return {
                "summary": summary_json,
                "error": "Failed to parse as JSON"
            } 