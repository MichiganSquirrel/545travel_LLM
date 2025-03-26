import json
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from models.clustering_model import ClusteringModel

class RecommendationAgent:
    def __init__(self, memory_bank, history):
        self.llm = OpenAI(temperature=0.7)
        self.memory_bank = memory_bank
        self.history = history
        self.clustering_model = ClusteringModel()
        
    def generate_recommendations(self, travel_plan):
        """Generate personalized recommendations based on user preferences and history"""
        
        # Load the recommendation template
        with open("templates/recommendation.txt", "r") as f:
            template = f.read()
        
        # Get similar past trips using clustering
        similar_trips = self.clustering_model.find_similar_trips(travel_plan, self.history)
        
        prompt = PromptTemplate(
            input_variables=["travel_plan", "user_preferences", "similar_trips"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Generate recommendations
        recommendations_json = chain.run(
            travel_plan=json.dumps(travel_plan),
            user_preferences=json.dumps(self.memory_bank.get("preferences", {})),
            similar_trips=json.dumps(similar_trips)
        )
        
        try:
            return json.loads(recommendations_json)
        except:
            return {
                "hotels": ["推荐解析失败"],
                "restaurants": ["推荐解析失败"],
                "attractions": ["推荐解析失败"],
                "error": "Failed to parse recommendations as JSON"
            } 