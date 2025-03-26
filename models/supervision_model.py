import json
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class SupervisionModel:
    def __init__(self):
        self.llm = OpenAI(temperature=0.2)
        
    def analyze_conversation(self, conversation, current_memory_bank):
        """Analyze conversation to extract and update user preferences"""
        
        # Load the preference extraction template
        with open("templates/preference_extraction.txt", "r") as f:
            template = f.read()
        
        prompt = PromptTemplate(
            input_variables=["conversation", "current_preferences"],
            template=template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # Extract updated preferences
        updated_preferences_json = chain.run(
            conversation=json.dumps(conversation),
            current_preferences=json.dumps(current_memory_bank.get("preferences", {}))
        )
        
        try:
            updated_preferences = json.loads(updated_preferences_json)
            
            # Merge with existing memory bank
            merged_memory_bank = current_memory_bank.copy()
            merged_memory_bank["preferences"] = updated_preferences
            
            return merged_memory_bank
        except:
            # If parsing fails, return current memory bank with error note
            current_memory_bank["error"] = "Failed to update preferences"
            return current_memory_bank 