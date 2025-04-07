import datetime
import pandas as pd
import json
import os
import re

def fix_existing_temp_file(user_id):
    """
    Ensure the user's temp.csv file exists and contains the 'user_preferences' column.
    If the file is found and the column is missing, the function adds it with an empty JSON object.
    
    Args:
        user_id: Identifier for the user.

    Returns:
        None
    """
    try:
        # Import database manager (assumes a custom module for handling user-specific data directories)
        from database.db_manager import DatabaseManager

        # Instantiate the database manager
        db_manager = DatabaseManager()

        # Construct the path to the user's temp.csv file
        user_dir = db_manager._get_user_dir(user_id)
        temp_file_path = os.path.join(user_dir, "temp.csv")

        # Check if temp.csv exists
        if os.path.exists(temp_file_path):
            try:
                # Load the existing CSV file into a DataFrame
                df = pd.read_csv(temp_file_path)

                # If 'user_preferences' column is missing, add it with an empty dictionary as string
                if "user_preferences" not in df.columns:
                    df["user_preferences"] = json.dumps({})  # Add column with default value

                    # Overwrite the file with the updated DataFrame
                    df.to_csv(temp_file_path, index=False)

            except Exception as e:
                # Handle any errors that occur while reading or updating the CSV
                raise Exception(f"Error fixing temp.csv: {str(e)}")
    except Exception as e:
        # Handle any errors during path resolution or outer logic
        raise Exception(f"Error in fix_existing_temp_file: {str(e)}")

def save_user_selection(user_query, selected_flight, all_flights, user_feedback):
    """
    Save user's selected flight and preferences to a temporary file and recommendation database.
    Returns a result dictionary with status and any relevant messages.
    """
    import os
    import json
    import traceback
    import pandas as pd
    from database.db_manager import DatabaseManager

    result = {
        "status": False,
        "messages": [],
        "temp_file": None,
        "recommend_file": None,
        "user_id": None,
        "error": None,
        "traceback": None
    }

    try:
        # Determine user_id
        user_id = user_query.get("user_id") or "unknown"
        user_query["user_id"] = user_id
        result["user_id"] = user_id

        # Fix or initialize the temp file
        fix_existing_temp_file(user_id)

        # Initialize database manager and save temp data
        db_manager = DatabaseManager()
        temp_file, tempdata = db_manager.save_temp_data(user_query, selected_flight, all_flights)
        result["temp_file"] = temp_file

        # Verify temp file exists
        if not temp_file or not os.path.exists(temp_file):
            result["messages"].append(f"Failed to create temp file: {temp_file}")
            return result, tempdata

        # Ensure the temp file has a 'user_preferences' column
        try:
            df = pd.read_csv(temp_file)
            if "user_preferences" not in df.columns:
                df["user_preferences"] = json.dumps({})
                df.to_csv(temp_file, index=False)
                result["messages"].append("'user_preferences' column added to temp.csv")
        except Exception as e:
            result["messages"].append(f"Error updating temp.csv: {str(e)}")

        # Create travel plan using selected flight info
        if selected_flight:
            essential_flight_info = {
                "flight_index": all_flights.index(selected_flight),
                "price": selected_flight.get("price", {}).get("total", "N/A"),
                "currency": selected_flight.get("price", {}).get("currency", "USD"),
                "cabin": selected_flight.get("travelerPricings", [{}])[0]
                    .get("fareDetailsBySegment", [{}])[0].get("cabin", "N/A"),
                "baggage": selected_flight.get("travelerPricings", [{}])[0]
                    .get("fareDetailsBySegment", [{}])[0]
                    .get("includedCheckedBags", {}).get("quantity", 0),
                "segments": []
            }

            for itinerary in selected_flight.get("itineraries", []):
                for segment in itinerary.get("segments", []):
                    essential_flight_info["segments"].append({
                        "carrier": segment.get("carrierCode", "N/A"),
                        "flight_number": segment.get("number", "N/A"),
                        "departure": {
                            "airport": segment.get("departure", {}).get("iataCode", "N/A"),
                            "time": segment.get("departure", {}).get("at", "N/A")
                        },
                        "arrival": {
                            "airport": segment.get("arrival", {}).get("iataCode", "N/A"),
                            "time": segment.get("arrival", {}).get("at", "N/A")
                        }
                    })

            travel_plan = {
                "destination": user_query.get("destination", ""),
                "departure_date": user_query.get("departure_date", ""),
                "return_date": user_query.get("return_date", ""),
                "flight": essential_flight_info,
                "detailed_plan": {
                    "activities": ["Visit attractions", "Try local food", "Shopping"],
                    "accommodation": "Comfortable hotel",
                    "transportation": "Taxi and public transit"
                }
            }

            recommend_file = db_manager.save_recommendation(user_id, travel_plan, user_feedback)
            result["recommend_file"] = recommend_file
            result["messages"].append("Travel plan saved to recommendation database.")

        result["status"] = True
        result["messages"].append("Session data saved successfully.")
        return result, tempdata

    except Exception as e:
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
        result["messages"].append(f"Error saving session data: {str(e)}")
        return result, None



def load_airport_data():
    """Load the airport dataset and prepare city-airport display format."""
    try:
        df = pd.read_csv("airports-code@public.csv", delimiter=";")
        df = df.rename(columns={"Airport Code": "IATA Code"})  # ensure consistency
        df["City-Airport"] = df["City Name"] + " (" + df["IATA Code"] + ")"
        return df
    except Exception as e:
        print(f"Error: loading airport data: {e}")
        # Fallback if CSV fails
        data = {
            "City Name": ["New York", "Los Angeles", "London", "Paris", "Tokyo", "Sydney"],
            "IATA Code": ["JFK", "LAX", "LHR", "CDG", "HND", "SYD"]
        }
        df = pd.DataFrame(data)
        df["City-Airport"] = df["City Name"] + " (" + df["IATA Code"] + ")"
        return df


def get_airport_code(city_airport_str):
    """Extract IATA code from formatted string 'City (IATA)'."""
    if "(" in city_airport_str and ")" in city_airport_str:
        return city_airport_str.split("(")[-1].replace(")", "").strip()
    return None

def format_datetime(datetime_str):
    """Format datetime string from API to a more readable format."""
    if not datetime_str:
        return "N/A"
    # Parse the ISO format and convert to a readable format
    try:
        dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return datetime_str
    
def format_datetime_short(datetime_str):
    """Format datetime string to a shorter format for tables."""
    if not datetime_str or datetime_str == 'N/A':
        return "N/A"
    # Parse the ISO format and convert to a readable format
    try:
        dt = datetime.datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%m/%d %H:%M")
    except:
        return datetime_str
    
def analyze_flights_without_llm(flights, user_query):
    """Generate a basic flight analysis without using LLM API"""
    origin = user_query.get("origin", "Not specified")
    destination = user_query.get("destination", "Not specified")
    
    # Create basic analysis
    analysis = f"""
## Flight Options Analysis

We found {len(flights)} flight options from {origin} to {destination}.

### Flight Comparison Table:

| Option | Airline | Duration (Outbound/Return) | Total Price | Baggage Allowance | Stops | Fare Type | Advantage |
|--------|---------|----------------------------|-------------|-------------------|-------|-----------|-----------|
"""
    
    # Add up to 5 flights to the table
    for i, flight in enumerate(flights[:5], 1):
        price = flight.get('price', {}).get('total', 'N/A')
        currency = flight.get('price', {}).get('currency', 'EUR')
        
        # Extract airline information
        airlines = []
        outbound_duration = "N/A"
        return_duration = "N/A"
        outbound_stops = 0
        return_stops = 0
        fare_type = "ECONOMY"  # Default value
        baggage = "1 piece"    # Default value
        
        # Simple advantage based on index
        advantage = f"Option {i}"
        
        # Extract flight details
        itineraries = flight.get('itineraries', [])
        if len(itineraries) >= 1:
            # Process outbound flight
            outbound = itineraries[0]
            outbound_segments = outbound.get('segments', [])
            outbound_stops = len(outbound_segments) - 1
            
            # Extract airlines
            for segment in outbound_segments:
                airline = segment.get('carrierCode', 'Unknown')
                if airline not in airlines:
                    airlines.append(airline)
            
            # Extract total duration
            outbound_duration = outbound.get('duration', 'N/A')
            if outbound_duration.startswith('PT'):
                # Convert ISO 8601 duration format
                outbound_duration = outbound_duration[2:].replace('H', 'h ').replace('M', 'm')
        
        if len(itineraries) >= 2:
            # Process return flight
            return_flight = itineraries[1]
            return_segments = return_flight.get('segments', [])
            return_stops = len(return_segments) - 1
            
            # Extract airlines
            for segment in return_segments:
                airline = segment.get('carrierCode', 'Unknown')
                if airline not in airlines:
                    airlines.append(airline)
            
            # Extract total duration
            return_duration = return_flight.get('duration', 'N/A')
            if return_duration.startswith('PT'):
                # Convert ISO 8601 duration format
                return_duration = return_duration[2:].replace('H', 'h ').replace('M', 'm')
        
        # Set baggage allowance and fare type based on airline
        airline_str = ", ".join(airlines) if airlines else "N/A"
        
        # Check for baggage allowance
        traveler_pricings = flight.get('travelerPricings', [])
        if traveler_pricings:
            traveler = traveler_pricings[0]
            fare_details = traveler.get('fareDetailsBySegment', [])
            if fare_details:
                included_baggage = fare_details[0].get('includedCheckedBags', {})
                if included_baggage:
                    baggage_quantity = included_baggage.get('quantity', 0)
                    baggage = f"{baggage_quantity} piece{'s' if baggage_quantity > 1 else ''}"
                
                # Get fare type
                cabin = fare_details[0].get('cabin', '')
                if cabin:
                    fare_type = cabin
        
        # Add to table
        analysis += f"| {i} | {airline_str} | {outbound_duration} / {return_duration} | {price} {currency} | {baggage} | {outbound_stops} stops | {fare_type} | {advantage} |\n"
    
    # Add simple note
    analysis += """
### Note:
Please see the detailed information for each flight option below.
"""
    
    # Add detailed information
    analysis += "\n### Detailed Flight Information:\n\n"
    
    for i, flight in enumerate(flights[:5], 1):
        price = flight.get('price', {}).get('total', 'N/A')
        currency = flight.get('price', {}).get('currency', 'EUR')
        
        analysis += f"#### Option {i}: {price} {currency}\n"
        
        itineraries = flight.get('itineraries', [])
        if itineraries:
            for j, itinerary in enumerate(itineraries):
                segments = itinerary.get('segments', [])
                if segments:
                    analysis += f"**{'Outbound' if j == 0 else 'Return'} Journey:**\n"
                    
                    for k, segment in enumerate(segments):
                        departure = segment.get('departure', {})
                        arrival = segment.get('arrival', {})
                        carrier = segment.get('carrierCode', 'N/A')
                        flight_number = segment.get('number', 'N/A')
                        
                        dep_time = format_datetime(departure.get('at', 'N/A'))
                        arr_time = format_datetime(arrival.get('at', 'N/A'))
                        dep_airport = departure.get('iataCode', 'N/A')
                        arr_airport = arrival.get('iataCode', 'N/A')
                        
                        analysis += f"- Segment {k+1}: {carrier} {flight_number}, {dep_airport} → {arr_airport}, Departure: {dep_time}, Arrival: {arr_time}\n"
                    
                    analysis += "\n"
        
        analysis += "---\n"
    
    return analysis    

def format_duration(iso_duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso_duration)
    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    return f"{hours}h {minutes}m"

def format_time(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str)
        return dt.strftime('%b %d, %Y at %I:%M %p')
    except:
        return dt_str  # fallback in case format is unexpected