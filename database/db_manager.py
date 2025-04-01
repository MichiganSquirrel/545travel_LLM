import os
import pandas as pd
import json
import datetime
import logging
from typing import Dict, List, Any, Optional

# Import LLM API
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.llm_api import LLMApi

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger("db_manager")

class DatabaseManager:
    """Database manager for handling user session data with improved structure"""
    
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
        
        # Try to initialize LLM API
        try:
            self.llm_api = LLMApi()
            logger.info("Successfully connected to LLM API for database operations")
        except Exception as e:
            logger.error(f"Failed to initialize LLM API: {str(e)}")
            self.llm_api = None
    
    def _get_user_dir(self, user_id: str) -> str:
        """
        Get or create user directory
        
        Args:
            user_id: User ID
            
        Returns:
            Path to user directory
        """
        user_dir = os.path.join(self.database_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def filter_flight_data_with_llm(self, selected_flight: Dict[str, Any], all_flights: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Use LLM to extract important information from flight data
        
        Args:
            selected_flight: User selected flight
            all_flights: All flight options
            
        Returns:
            Filtered flight data
        """
        # If LLM API is not available, return simplified data
        if self.llm_api is None:
            return self._manual_filter_flight_data(selected_flight)
        
        try:
            # Construct prompt
            prompt = f"""Extract the most important information from the following flight data, removing redundant data.
            Retain the following key information:
            1. Flight number, airline code
            2. Departure/arrival times, airport codes
            3. Price information
            4. Baggage allowance
            5. Cabin type
            6. Number and type of segments
            
            Please return the streamlined data in JSON format, without including redundant repeated information.
            
            Flight data: {json.dumps(selected_flight, ensure_ascii=False)}
            """
            
            # Call LLM API
            logger.info("Sending request to LLM to filter flight data")
            response = self.llm_api.generate_text(prompt, max_tokens=2000, temperature=0.1)
            
            # Parse response
            if "error" in response:
                logger.error(f"Error in LLM response: {response['error']}")
                return self._manual_filter_flight_data(selected_flight)
                
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error("Empty content received from LLM API")
                return self._manual_filter_flight_data(selected_flight)
            
            # Extract JSON part
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL) or re.search(r'```(.*?)```', content, re.DOTALL) or re.search(r'{.*}', content, re.DOTALL)
            
            if json_match:
                filtered_json = json_match.group(1) if json_match.group(1).strip().startswith('{') else json_match.group(0)
                try:
                    filtered_data = json.loads(filtered_json)
                    logger.info(f"Successfully filtered flight data with LLM (reduced to {len(json.dumps(filtered_data))} chars)")
                    return filtered_data
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from LLM response: {content}")
                    return self._manual_filter_flight_data(selected_flight)
            else:
                # Try to parse the entire content as JSON
                try:
                    filtered_data = json.loads(content)
                    logger.info(f"Successfully filtered flight data with LLM (reduced to {len(json.dumps(filtered_data))} chars)")
                    return filtered_data
                except:
                    logger.error(f"No JSON pattern found in LLM response: {content}")
                    return self._manual_filter_flight_data(selected_flight)
                    
        except Exception as e:
            logger.error(f"Error filtering flight data with LLM: {str(e)}")
            return self._manual_filter_flight_data(selected_flight)
    
    def _manual_filter_flight_data(self, flight_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Manually filter flight data (fallback when LLM is not available)
        
        Args:
            flight_data: Original flight data
            
        Returns:
            Filtered flight data
        """
        filtered_data = {}
        
        # Extract basic information
        if "price" in flight_data:
            filtered_data["price"] = {
                "total": flight_data["price"].get("total", "N/A"),
                "currency": flight_data["price"].get("currency", "USD")
            }
        
        # Extract itinerary information
        if "itineraries" in flight_data:
            filtered_data["itineraries"] = []
            for itinerary in flight_data["itineraries"]:
                filtered_itinerary = {"duration": itinerary.get("duration", "N/A"), "segments": []}
                
                if "segments" in itinerary:
                    for segment in itinerary["segments"]:
                        filtered_segment = {
                            "carrierCode": segment.get("carrierCode", "N/A"),
                            "number": segment.get("number", "N/A"),
                            "departure": {
                                "iataCode": segment.get("departure", {}).get("iataCode", "N/A"),
                                "at": segment.get("departure", {}).get("at", "N/A")
                            },
                            "arrival": {
                                "iataCode": segment.get("arrival", {}).get("iataCode", "N/A"),
                                "at": segment.get("arrival", {}).get("at", "N/A")
                            }
                        }
                        filtered_itinerary["segments"].append(filtered_segment)
                
                filtered_data["itineraries"].append(filtered_itinerary)
        
        # Extract traveler pricing information
        if "travelerPricings" in flight_data and flight_data["travelerPricings"]:
            traveler = flight_data["travelerPricings"][0]
            cabin_info = {}
            
            if "fareDetailsBySegment" in traveler and traveler["fareDetailsBySegment"]:
                segment = traveler["fareDetailsBySegment"][0]
                cabin_info["cabin"] = segment.get("cabin", "ECONOMY")
                
                if "includedCheckedBags" in segment:
                    cabin_info["baggage"] = segment["includedCheckedBags"].get("quantity", 0)
                    
            filtered_data["cabin_info"] = cabin_info
            
        logger.info(f"Manually filtered flight data (reduced to {len(json.dumps(filtered_data))} chars)")
        return filtered_data
    
    def save_temp_data(self, user_query: Dict[str, Any], 
                    selected_flight: Optional[Dict[str, Any]], 
                    all_flights: List[Dict[str, Any]]) -> str:
        """
        Save temporary session data to temp.csv file in user directory
        
        Args:
            user_query: User query information
            selected_flight: User selected flight (optional)
            all_flights: All flight options
            
        Returns:
            Path to the saved file
        """
        user_id = user_query.get("user_id", "unknown")
        user_dir = self._get_user_dir(user_id)
        
        # Create filepath
        filename = os.path.join(user_dir, "temp.csv")
        
        # Filter flight data to keep only important information
        if selected_flight:
            logger.info("Filtering selected flight data to remove unnecessary information")
            filtered_selected_flight = self.filter_flight_data_with_llm(selected_flight, all_flights)
        else:
            filtered_selected_flight = None
        
        # Use simplified version of all_flights data - keep only the most basic information
        simplified_all_flights = []
        for i, flight in enumerate(all_flights[:5]):  # Keep only the top 5 flights
            simplified_flight = {
                "index": i,
                "price": flight.get("price", {}).get("total", "N/A"),
                "currency": flight.get("price", {}).get("currency", "USD")
            }
            
            # Add basic flight information
            if "itineraries" in flight and flight["itineraries"] and "segments" in flight["itineraries"][0]:
                first_segment = flight["itineraries"][0]["segments"][0]
                simplified_flight["carrier"] = first_segment.get("carrierCode", "N/A")
                simplified_flight["flight_number"] = first_segment.get("number", "N/A")
                
            simplified_all_flights.append(simplified_flight)
            
        # Prepare session data
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_data = {
            "timestamp": timestamp,
            "origin": user_query.get("origin", ""),
            "destination": user_query.get("destination", ""),
            "departure_date": user_query.get("departure_date", ""),
            "return_date": user_query.get("return_date", ""),
            "all_flights_count": len(all_flights),
            "selected_flight": "None" if filtered_selected_flight is None else json.dumps(filtered_selected_flight),
            "all_flights": json.dumps(simplified_all_flights)  # Use simplified flight list
        }
        
        # Write data to CSV file
        df = pd.DataFrame([session_data])
        df.to_csv(filename, index=False)
        
        logger.info(f"Saved filtered flight data to {filename}")
        return filename
    
    def update_temp_with_preferences(self, user_id: str, user_preferences: Dict[str, Any]) -> str:
        """
        Update temp.csv with user's additional travel preferences
        
        Args:
            user_id: User ID
            user_preferences: User's additional travel preferences (e.g., accommodation, activities)
            
        Returns:
            Path to the updated file
        """
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "temp.csv")
        
        logger.info(f"Attempting to update temp.csv with preferences for user {user_id}")
        logger.info(f"File path: {filename}")
        
        # Check if file exists
        if not os.path.exists(filename):
            logger.warning(f"Temp file {filename} does not exist for user {user_id}, creating it")
            
            # Create a new file with minimal structure
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            initial_data = {
                "timestamp": timestamp,
                "user_id": user_id,
                "origin": user_preferences.get("origin", ""),
                "destination": user_preferences.get("destination", ""),
                "departure_date": user_preferences.get("departure_date", ""),
                "return_date": user_preferences.get("return_date", "")
            }
            
            # Create the initial dataframe
            df = pd.DataFrame([initial_data])
            
            # Process user preferences
            processed_preferences = self._process_preferences_with_llm(user_preferences)
            
            # Add preferences as JSON
            df["user_preferences"] = json.dumps(processed_preferences)
            
            # Save to CSV
            df.to_csv(filename, index=False)
            logger.info(f"Created new temp file with preferences: {filename}")
            return filename
            
        try:
            # Read existing data
            logger.info(f"Reading existing temp file: {filename}")
            
            try:
                existing_df = pd.read_csv(filename)
                logger.info(f"Successfully read temp file with {len(existing_df)} rows")
            except pd.errors.EmptyDataError:
                logger.warning(f"Empty CSV file: {filename}")
                # Handle empty file case - create new dataframe
                existing_df = pd.DataFrame(columns=["timestamp", "user_id", "origin", "destination", 
                                                  "departure_date", "return_date"])
            
            if existing_df.empty:
                logger.warning(f"Empty dataframe after reading {filename}")
                # Create a new row if the dataframe is empty
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_row = {
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "origin": user_preferences.get("origin", ""),
                    "destination": user_preferences.get("destination", ""),
                    "departure_date": user_preferences.get("departure_date", ""),
                    "return_date": user_preferences.get("return_date", "")
                }
                existing_df = pd.DataFrame([new_row])
                logger.info(f"Created new row for empty dataframe")
                
            # Process user preferences
            logger.info(f"Processing user preferences with LLM")
            processed_preferences = self._process_preferences_with_llm(user_preferences)
            
            # Convert preferences to JSON string
            preferences_json = json.dumps(processed_preferences)
            logger.info(f"Converted preferences to JSON (length: {len(preferences_json)})")
            
            # FIXED: Only update the most recent row, not all rows
            # Get the most recent row (last row)
            if len(existing_df) > 0:
                last_row_idx = len(existing_df) - 1
                # Update only the most recent row with the preferences
                existing_df.at[last_row_idx, "user_preferences"] = preferences_json
                logger.info(f"Updated user_preferences for row {last_row_idx}")
            else:
                # If there are somehow no rows after the previous checks, add a new row
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_row = {
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "origin": user_preferences.get("origin", ""),
                    "destination": user_preferences.get("destination", ""),
                    "departure_date": user_preferences.get("departure_date", ""),
                    "return_date": user_preferences.get("return_date", ""),
                    "user_preferences": preferences_json
                }
                # Append the new row to the dataframe
                existing_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
                logger.info("Added new row with preferences")
            
            # Save updated dataframe back to CSV
            existing_df.to_csv(filename, index=False)
            logger.info(f"Saved updated dataframe to {filename}")
            
            # Verify the file was saved correctly
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                logger.info(f"Successfully updated temp file: {filename}")
                return filename
            else:
                logger.error(f"File verification failed after save: {filename}")
                return ""
            
        except Exception as e:
            logger.error(f"Error updating temp file with preferences: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ""
            
    def _process_preferences_with_llm(self, preferences: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process user preferences with LLM to extract important information
        
        Args:
            preferences: User's raw preference data
            
        Returns:
            Processed preference data
        """
        # If LLM API is not available, return original preferences
        if self.llm_api is None:
            return preferences
            
        try:
            # Construct prompt
            prompt = f"""Extract and organize the most important information from the following travel preferences:
            
            {json.dumps(preferences, ensure_ascii=False)}
            
            Categorize them into:
            1. Accommodation preferences (hotel type, location, amenities)
            2. Activity preferences (sightseeing, adventure, cultural, relaxation)
            3. Dining preferences (cuisine types, dining style)
            4. Transportation preferences
            5. Special requirements
            
            Return only the organized data in JSON format.
            """
            
            # Call LLM API
            logger.info("Sending request to LLM to process preferences")
            response = self.llm_api.generate_text(prompt, max_tokens=1000, temperature=0.1)
            
            # Parse response
            if "error" in response:
                logger.error(f"Error in LLM response: {response['error']}")
                return preferences
                
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error("Empty content received from LLM API")
                return preferences
                
            # Extract JSON
            import re
            json_match = re.search(r'```json\n(.*?)\n```', content, re.DOTALL) or re.search(r'```(.*?)```', content, re.DOTALL) or re.search(r'{.*}', content, re.DOTALL)
            
            if json_match:
                filtered_json = json_match.group(1) if json_match.group(1).strip().startswith('{') else json_match.group(0)
                try:
                    processed_data = json.loads(filtered_json)
                    logger.info(f"Successfully processed preferences with LLM")
                    return processed_data
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON from LLM response: {content}")
                    return preferences
            else:
                # Try to parse the entire content as JSON
                try:
                    processed_data = json.loads(content)
                    logger.info(f"Successfully processed preferences with LLM")
                    return processed_data
                except:
                    logger.error(f"No JSON pattern found in LLM response: {content}")
                    return preferences
                    
        except Exception as e:
            logger.error(f"Error processing preferences with LLM: {str(e)}")
            return preferences
    
    def update_memory_bank(self, user_id: str, preferences: Dict[str, Any]) -> str:
        """
        Update user preferences in memory_bank.csv using supervision model results
        
        Args:
            user_id: User ID
            preferences: User preferences extracted by supervision model
            
        Returns:
            Path to the memory bank file
        """
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "memory_bank.csv")
        
        # Current timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Format preferences for CSV storage
        preference_data = {
            "timestamp": timestamp,
            "user_id": user_id
        }
        
        # Flatten preferences for CSV storage
        for category, values in preferences.items():
            if isinstance(values, dict):
                for key, value in values.items():
                    preference_data[f"{category}_{key}"] = value
            elif isinstance(values, list):
                preference_data[category] = json.dumps(values)
            else:
                preference_data[category] = values
        
        # Check if file exists to append or create new
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
    
    def save_recommendation(self, user_id: str, 
                           travel_plan: Dict[str, Any], 
                           user_feedback: str) -> str:
        """
        Save successful travel plans to recommend.csv for clustering analysis
        
        Args:
            user_id: User ID
            travel_plan: The finalized travel plan
            user_feedback: User feedback on the plan
            
        Returns:
            Path to the recommend file
        """
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "recommend.csv")
        
        # Current timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Basic plan data
        plan_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "destination": travel_plan.get("destination", ""),
            "departure_date": travel_plan.get("departure_date", ""),
            "return_date": travel_plan.get("return_date", ""),
            "user_feedback": user_feedback,
            "travel_plan": json.dumps(travel_plan)
        }
        
        # Check if file exists to append or create new
        if os.path.exists(filename):
            # Read existing data
            existing_df = pd.read_csv(filename)
            # Append new data
            updated_df = pd.concat([existing_df, pd.DataFrame([plan_data])], ignore_index=True)
            updated_df.to_csv(filename, index=False)
        else:
            # Create new file
            pd.DataFrame([plan_data]).to_csv(filename, index=False)
            
        return filename
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user recommendation history from recommend.csv
        
        Args:
            user_id: User ID
            
        Returns:
            List of user's previous travel plans
        """
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
            history = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Parse JSON fields
                if "travel_plan" in item:
                    try:
                        item["travel_plan"] = json.loads(item["travel_plan"])
                    except:
                        pass
                history.append(item)
            
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return history
        except Exception as e:
            print(f"Error reading recommend file: {str(e)}")
            return []
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Get user preferences from memory_bank.csv
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of user preferences
        """
        user_dir = self._get_user_dir(user_id)
        memory_bank_file = os.path.join(user_dir, "memory_bank.csv")
        
        if not os.path.exists(memory_bank_file):
            return {
                "frequent_destinations": {},
                "preferred_airlines": {},
                "cabin_class": {},
                "typical_trip_duration": []
            }
            
        try:
            # Read the CSV file
            df = pd.read_csv(memory_bank_file)
            if df.empty:
                return {
                    "frequent_destinations": {},
                    "preferred_airlines": {},
                    "cabin_class": {},
                    "typical_trip_duration": []
                }
            
            # Get the most recent entry
            latest_entry = df.iloc[-1].to_dict()
            
            # Parse and reconstruct preferences
            preferences = {
                "frequent_destinations": {},
                "preferred_airlines": {},
                "cabin_class": {},
                "typical_trip_duration": []
            }
            
            # Reconstruct nested dictionaries from flattened columns
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
            
            return preferences
        except Exception as e:
            print(f"Error reading memory bank file: {str(e)}")
            return {
                "frequent_destinations": {},
                "preferred_airlines": {},
                "cabin_class": {},
                "typical_trip_duration": []
            }
    
    # Legacy method for backward compatibility
    def save_session(self, user_query: Dict[str, Any], 
                    selected_flight: Optional[Dict[str, Any]], 
                    all_flights: List[Dict[str, Any]], 
                    user_feedback: str) -> str:
        """
        Legacy method that now calls both save_temp_data and update_memory_bank
        """
        # Save temp data
        temp_file = self.save_temp_data(user_query, selected_flight, all_flights)
        
        # Extract basic preferences from this session
        user_id = user_query.get("user_id", "unknown")
        preferences = {
            "frequent_destinations": {
                user_query.get("destination", ""): 1
            },
            "typical_trip_duration": []
        }
        
        # If there's a selected flight, extract more preferences
        if selected_flight:
            # Extract cabin class if available
            cabin_class = None
            if "travelerPricings" in selected_flight and selected_flight["travelerPricings"]:
                if "fareDetailsBySegment" in selected_flight["travelerPricings"][0]:
                    segments = selected_flight["travelerPricings"][0]["fareDetailsBySegment"]
                    if segments and "cabin" in segments[0]:
                        cabin_class = segments[0]["cabin"]
                        
            if cabin_class:
                preferences["cabin_class"] = {cabin_class: 1}
                
            # Extract airlines if available
            if "itineraries" in selected_flight:
                for itinerary in selected_flight["itineraries"]:
                    for segment in itinerary.get("segments", []):
                        airline = segment.get("carrierCode")
                        if airline:
                            if "preferred_airlines" not in preferences:
                                preferences["preferred_airlines"] = {}
                            preferences["preferred_airlines"][airline] = preferences["preferred_airlines"].get(airline, 0) + 1
        
        # Update memory bank with these basic preferences
        self.update_memory_bank(user_id, preferences)
        
        return temp_file 