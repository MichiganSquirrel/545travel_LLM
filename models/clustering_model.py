import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class ClusteringModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
    
    def find_similar_trips(self, current_plan, history, top_n=3):
        """Find similar trips from history using text similarity"""
        if not history:
            return []
        
        # Extract text features from current plan
        current_plan_text = self._extract_text_features(current_plan)
        
        # Extract text features from historical plans
        history_texts = [self._extract_text_features(item["plan"]) for item in history]
        
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
        except:
            # Return empty list if vectorization fails
            return []
    
    def _extract_text_features(self, plan):
        """Extract text features from a travel plan"""
        # This is a simple implementation - you might want to improve this
        # based on the actual structure of your travel plans
        text_features = []
        
        # Extract destination
        if "destination" in plan:
            text_features.append(str(plan["destination"]))
        
        # Extract activities
        if "detailed_plan" in plan and "activities" in plan["detailed_plan"]:
            for activity in plan["detailed_plan"]["activities"]:
                text_features.append(str(activity))
        
        # Extract other relevant features
        # ...
        
        return " ".join(text_features) 