import numpy as np
import os
import pandas as pd
import json
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import List, Dict, Any, Optional

class ClusteringModel:
    def __init__(self, database_dir: Optional[str] = None):
        self.vectorizer = TfidfVectorizer()
        
        # Set up database directory
        if database_dir:
            self.database_dir = database_dir
        else:
            # Default to database folder in project root
            self.database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        
        # Ensure database directory exists
        os.makedirs(self.database_dir, exist_ok=True)
    
    def _get_user_dir(self, user_id: str) -> str:
        """Get user directory path"""
        return os.path.join(self.database_dir, f"user_{user_id}")
    
    def find_similar_trips(self, current_plan: Dict[str, Any], user_id: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        Find similar trips from user's recommend.csv file using text similarity
        
        Args:
            current_plan: Current travel plan
            user_id: User ID
            top_n: Number of similar plans to return
            
        Returns:
            List of similar plans
        """
        # Get all historical plans from recommend.csv
        history = self.get_user_recommendations(user_id)
        
        if not history:
            return []
        
        # Extract text features from current plan
        current_plan_text = self._extract_text_features(current_plan)
        
        # Extract text features from historical plans
        history_texts = []
        for item in history:
            if "travel_plan" in item:
                history_texts.append(self._extract_text_features(item["travel_plan"]))
        
        if not history_texts:
            return []
        
        # Create a combined corpus
        all_texts = [current_plan_text] + history_texts
        
        # Fit and transform the vectorizer
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # Calculate similarity between current plan and all historical plans
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # Get indices of top similar plans
            top_indices = similarities.argsort()[-top_n:][::-1]
            
            # Return top similar plans
            return [history[i] for i in top_indices]
        except Exception as e:
            print(f"Error in clustering: {str(e)}")
            # Return empty list if vectorization fails
            return []
    
    def get_user_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user recommendations from recommend.csv file"""
        user_dir = self._get_user_dir(user_id)
        recommend_file = os.path.join(user_dir, "recommend.csv")
        
        if not os.path.exists(recommend_file):
            return []
            
        try:
            # Read the CSV file
            df = pd.read_csv(recommend_file)
            if df.empty:
                return []
                
            # Convert to list of dictionaries
            recommendations = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Parse JSON fields
                if "travel_plan" in item and item["travel_plan"]:
                    try:
                        item["travel_plan"] = json.loads(item["travel_plan"])
                    except:
                        pass
                recommendations.append(item)
            
            return recommendations
        except Exception as e:
            print(f"Error reading recommend file: {str(e)}")
            return []
    
    def _extract_text_features(self, plan: Dict[str, Any]) -> str:
        """Extract text features from a travel plan"""
        text_features = []
        
        # Extract destination
        if "destination" in plan:
            text_features.append(str(plan["destination"]))
        
        # Extract activities
        if "detailed_plan" in plan and "activities" in plan["detailed_plan"]:
            for activity in plan["detailed_plan"]["activities"]:
                text_features.append(str(activity))
        
        # Extract interests if available
        if "interests" in plan:
            if isinstance(plan["interests"], list):
                for interest in plan["interests"]:
                    text_features.append(str(interest))
            else:
                text_features.append(str(plan["interests"]))
        
        # Extract accommodation details
        if "detailed_plan" in plan and "accommodation" in plan["detailed_plan"]:
            text_features.append(str(plan["detailed_plan"]["accommodation"]))
        
        # Extract transportation details
        if "detailed_plan" in plan and "transportation" in plan["detailed_plan"]:
            text_features.append(str(plan["detailed_plan"]["transportation"]))
        
        # Join all features with spaces
        return " ".join(text_features)
    
    def add_recommendation(self, user_id: str, travel_plan: Dict[str, Any], feedback: str = "") -> bool:
        """Add a new recommendation to the user's recommend.csv file"""
        user_dir = self._get_user_dir(user_id)
        os.makedirs(user_dir, exist_ok=True)
        recommend_file = os.path.join(user_dir, "recommend.csv")
        
        # Prepare data
        timestamp = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
        data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "destination": travel_plan.get("destination", ""),
            "departure_date": travel_plan.get("departure_date", ""),
            "return_date": travel_plan.get("return_date", ""),
            "feedback": feedback,
            "travel_plan": json.dumps(travel_plan)
        }
        
        try:
            # Check if file exists
            if os.path.exists(recommend_file):
                # Append to existing file
                df = pd.read_csv(recommend_file)
                df = pd.concat([df, pd.DataFrame([data])], ignore_index=True)
            else:
                # Create new file
                df = pd.DataFrame([data])
                
            # Save to file
            df.to_csv(recommend_file, index=False)
            return True
        except Exception as e:
            print(f"Error saving recommendation: {str(e)}")
            return False 