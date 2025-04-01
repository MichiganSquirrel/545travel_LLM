import json
import os
import pandas as pd
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from datetime import datetime
from typing import Dict, Any, List, Optional

class SupervisionModel:
    def __init__(self, database_dir: Optional[str] = None):
        self.llm = OpenAI(temperature=0.2)
        
        # Set up database directory
        if database_dir:
            self.database_dir = database_dir
        else:
            # Default to database folder in project root
            self.database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        
        # Ensure database directory exists
        os.makedirs(self.database_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id: str) -> str:
        """Create or get user directory"""
        user_dir = os.path.join(self.database_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
        
    def analyze_conversation(self, conversation: List[Dict[str, str]], user_id: str) -> Dict[str, Any]:
        """
        Analyze conversation to extract and update user preferences
        
        Args:
            conversation: List of conversation messages
            user_id: User ID
            
        Returns:
            Updated memory bank with preferences
        """
        # Get current memory bank
        current_memory_bank = self.get_memory_bank(user_id)
        
        # Check if template exists
        template_path = "templates/preference_extraction.txt"
        if os.path.exists(template_path):
            with open(template_path, "r") as f:
                template = f.read()
        else:
            # Fallback template if file doesn't exist
            template = """
            You are an AI assistant that analyzes travel conversations to extract user preferences.
            
            Conversation:
            {conversation}
            
            Current user preferences:
            {current_preferences}
            
            Based on the conversation, update the user preferences. Extract information about:
            1. Preferred destinations
            2. Preferred airlines
            3. Cabin class preferences
            4. Trip duration preferences
            5. Budget constraints
            6. Activity interests
            7. Accommodation preferences
            
            Return the updated preferences as a JSON object with these categories.
            """
        
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
            
            # Save to memory_bank.csv
            self.save_memory_bank(user_id, merged_memory_bank)
            
            return merged_memory_bank
        except Exception as e:
            # If parsing fails, return current memory bank with error note
            current_memory_bank["error"] = f"Failed to update preferences: {str(e)}"
            return current_memory_bank
    
    def get_memory_bank(self, user_id: str) -> Dict[str, Any]:
        """Get current memory bank from user's memory_bank.csv file"""
        user_dir = self._get_user_dir(user_id)
        memory_bank_file = os.path.join(user_dir, "memory_bank.csv")
        
        if not os.path.exists(memory_bank_file):
            # Return empty memory bank
            return {
                "preferences": {
                    "frequent_destinations": {},
                    "preferred_airlines": {},
                    "cabin_class": {},
                    "typical_trip_duration": [],
                    "budget_preference": "medium",
                    "activity_interests": [],
                    "accommodation_preferences": []
                }
            }
        
        try:
            # Read CSV file
            df = pd.read_csv(memory_bank_file)
            if df.empty:
                return {"preferences": {}}
            
            # Get latest entry
            latest_entry = df.iloc[-1].to_dict()
            
            # Reconstruct preferences from flattened structure
            preferences = {
                "frequent_destinations": {},
                "preferred_airlines": {},
                "cabin_class": {},
                "typical_trip_duration": [],
                "budget_preference": "medium",
                "activity_interests": [],
                "accommodation_preferences": []
            }
            
            # Parse columns back into structured data
            for key, value in latest_entry.items():
                if key.startswith("frequent_destinations_"):
                    dest = key.replace("frequent_destinations_", "")
                    preferences["frequent_destinations"][dest] = value
                elif key.startswith("preferred_airlines_"):
                    airline = key.replace("preferred_airlines_", "")
                    preferences["preferred_airlines"][airline] = value
                elif key.startswith("cabin_class_"):
                    cabin = key.replace("cabin_class_", "")
                    preferences["cabin_class"][cabin] = value
                elif key == "typical_trip_duration":
                    try:
                        preferences["typical_trip_duration"] = json.loads(value)
                    except:
                        preferences["typical_trip_duration"] = []
                elif key == "budget_preference":
                    preferences["budget_preference"] = value
                elif key == "activity_interests":
                    try:
                        preferences["activity_interests"] = json.loads(value)
                    except:
                        preferences["activity_interests"] = []
                elif key == "accommodation_preferences":
                    try:
                        preferences["accommodation_preferences"] = json.loads(value)
                    except:
                        preferences["accommodation_preferences"] = []
            
            return {"preferences": preferences}
        except Exception as e:
            print(f"Error reading memory bank: {str(e)}")
            return {"preferences": {}}
    
    def save_memory_bank(self, user_id: str, memory_bank: Dict[str, Any]) -> str:
        """Save memory bank to memory_bank.csv file"""
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "memory_bank.csv")
        
        # Current timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format preferences for CSV storage
        preference_data = {
            "timestamp": timestamp,
            "user_id": user_id
        }
        
        # Get preferences
        preferences = memory_bank.get("preferences", {})
        
        # Flatten preferences for CSV storage
        for category, values in preferences.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    preference_data[f"{category}_{key}"] = value
            elif isinstance(values, list):
                preference_data[category] = json.dumps(values)
            else:
                preference_data[category] = values
        
        # Check if file exists
        if os.path.exists(filename):
            # Read existing data
            existing_df = pd.read_csv(filename)
            # Append new data
            updated_df = pd.concat([existing_df, pd.DataFrame([preference_data])], ignore_index=True)
            updated_df.to_csv(filename, index=False)
        else:
            # Create new file
            pd.DataFrame([preference_data]).to_csv(filename, index=False)
        
        return filename 