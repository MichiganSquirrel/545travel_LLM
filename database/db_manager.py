import os
import pandas as pd
import json
import datetime
from typing import Dict, List, Any, Optional

class DatabaseManager:
    """Database manager for handling user session data"""
    
    def __init__(self, database_dir: Optional[str] = None):
        """
        Initialize the database manager
        
        Args:
            database_dir: Database directory path (optional)
        """
        if database_dir:
            self.database_dir = database_dir
        else:
            # Default to database folder in project root
            self.database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        
        # Ensure database directory exists
        os.makedirs(self.database_dir, exist_ok=True)
    
    def save_session(self, user_query: Dict[str, Any], 
                    selected_flight: Optional[Dict[str, Any]], 
                    all_flights: List[Dict[str, Any]], 
                    user_feedback: str) -> str:
        """
        Save user session data to CSV file
        
        Args:
            user_query: User query information
            selected_flight: User selected flight (optional)
            all_flights: All flight options
            user_feedback: User feedback
            
        Returns:
            Path to the saved file
        """
        # Create unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = user_query.get("user_id", "unknown")
        filename = os.path.join(self.database_dir, f"session_{user_id}_{timestamp}.csv")
        
        # Prepare session data
        session_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "origin": user_query.get("origin", ""),
            "destination": user_query.get("destination", ""),
            "departure_date": user_query.get("departure_date", ""),
            "return_date": user_query.get("return_date", ""),
            "user_feedback": user_feedback,
            "all_flights_count": len(all_flights),
            "selected_flight": "None" if selected_flight is None else json.dumps(selected_flight),
            "all_flights": json.dumps(all_flights)
        }
        
        # Write data to CSV file
        df = pd.DataFrame([session_data])
        df.to_csv(filename, index=False)
        
        return filename
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user flight search history
        
        Args:
            user_id: User ID
            
        Returns:
            List of user's previous sessions
        """
        history = []
        
        # Find all files for this user
        for filename in os.listdir(self.database_dir):
            if filename.startswith(f"session_{user_id}_") and filename.endswith(".csv"):
                file_path = os.path.join(self.database_dir, filename)
                try:
                    # Read the CSV file
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        # Convert to dictionary
                        session = df.iloc[0].to_dict()
                        
                        # Parse JSON fields
                        if "selected_flight" in session and session["selected_flight"] != "None":
                            try:
                                session["selected_flight"] = json.loads(session["selected_flight"])
                            except:
                                session["selected_flight"] = None
                        
                        history.append(session)
                except Exception as e:
                    print(f"Error reading file {file_path}: {str(e)}")
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return history
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Extract user preferences from history
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of user preferences
        """
        history = self.get_user_history(user_id)
        preferences = {
            "frequent_destinations": {},
            "preferred_airlines": {},
            "cabin_class": {},
            "typical_trip_duration": []
        }
        
        for session in history:
            # Count destinations
            destination = session.get("destination")
            if destination:
                if destination in preferences["frequent_destinations"]:
                    preferences["frequent_destinations"][destination] += 1
                else:
                    preferences["frequent_destinations"][destination] = 1
            
            # Extract selected flight info
            selected_flight = session.get("selected_flight")
            if selected_flight and isinstance(selected_flight, dict):
                # Count airlines
                for itinerary in selected_flight.get("itineraries", []):
                    for segment in itinerary.get("segments", []):
                        airline = segment.get("carrierCode")
                        if airline:
                            if airline in preferences["preferred_airlines"]:
                                preferences["preferred_airlines"][airline] += 1
                            else:
                                preferences["preferred_airlines"][airline] = 1
                
                # Count cabin class
                cabin = selected_flight.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", [{}])[0].get("cabin")
                if cabin:
                    if cabin in preferences["cabin_class"]:
                        preferences["cabin_class"][cabin] += 1
                    else:
                        preferences["cabin_class"][cabin] = 1
            
            # Calculate trip duration
            departure_date = session.get("departure_date")
            return_date = session.get("return_date")
            if departure_date and return_date:
                try:
                    d1 = datetime.datetime.strptime(departure_date, "%Y-%m-%d")
                    d2 = datetime.datetime.strptime(return_date, "%Y-%m-%d")
                    duration = (d2 - d1).days
                    preferences["typical_trip_duration"].append(duration)
                except:
                    pass
        
        # Calculate average trip duration
        if preferences["typical_trip_duration"]:
            preferences["average_trip_duration"] = sum(preferences["typical_trip_duration"]) / len(preferences["typical_trip_duration"])
        else:
            preferences["average_trip_duration"] = None
        
        return preferences 