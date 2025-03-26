import os
import json
from datetime import datetime

class DatabaseManager:
    def __init__(self, base_path="database/user_database"):
        self.base_path = base_path
        
    def ensure_user_exists(self, user_id):
        """Ensure user directory and files exist"""
        user_dir = os.path.join(self.base_path, user_id)
        
        # Create user directory if it doesn't exist
        if not os.path.exists(user_dir):
            os.makedirs(user_dir)
        
        # Create memory_bank.json if it doesn't exist
        memory_bank_path = os.path.join(user_dir, "memory_bank.json")
        if not os.path.exists(memory_bank_path):
            with open(memory_bank_path, 'w') as f:
                json.dump({"preferences": {}}, f, ensure_ascii=False, indent=2)
        
        # Create history.json if it doesn't exist
        history_path = os.path.join(user_dir, "history.json")
        if not os.path.exists(history_path):
            with open(history_path, 'w') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def load_memory_bank(self, user_id):
        """Load user memory bank"""
        memory_bank_path = os.path.join(self.base_path, user_id, "memory_bank.json")
        
        try:
            with open(memory_bank_path, 'r') as f:
                return json.load(f)
        except:
            # Return default if file can't be read
            return {"preferences": {}}
    
    def load_history(self, user_id):
        """Load user history"""
        history_path = os.path.join(self.base_path, user_id, "history.json")
        
        try:
            with open(history_path, 'r') as f:
                return json.load(f)
        except:
            # Return empty list if file can't be read
            return []
    
    def update_memory_bank(self, user_id, memory_bank):
        """Update user memory bank"""
        memory_bank_path = os.path.join(self.base_path, user_id, "memory_bank.json")
        
        with open(memory_bank_path, 'w') as f:
            json.dump(memory_bank, f, ensure_ascii=False, indent=2)
    
    def update_history(self, user_id, travel_plan):
        """Update user history with new travel plan"""
        history_path = os.path.join(self.base_path, user_id, "history.json")
        
        # Load current history
        current_history = self.load_history(user_id)
        
        # Add timestamp to travel plan
        travel_plan_with_timestamp = {
            "timestamp": datetime.now().isoformat(),
            "plan": travel_plan
        }
        
        # Add new plan to history
        current_history.append(travel_plan_with_timestamp)
        
        # Save updated history
        with open(history_path, 'w') as f:
            json.dump(current_history, f, ensure_ascii=False, indent=2) 