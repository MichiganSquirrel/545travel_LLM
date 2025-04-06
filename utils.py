import datetime
import pandas as pd
import json
import os

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