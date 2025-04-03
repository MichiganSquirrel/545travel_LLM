import streamlit as st
import pandas as pd
import datetime
import requests
import os
import json
import sys
import re
import time
import traceback 

# Add project root directory to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import configuration and API
from config import load_api_keys
from api.llm_api import LLMApi

# First load API keys
load_api_keys()

# Get API credentials from environment variables or set them directly
# Note: For better security, use environment variables instead of hardcoding
AMADEUS_API_KEY = os.environ.get("AMADEUS_API_KEY", "wnkJALiAYNo4duZVG88dgfI6H2jtGGG2")
AMADEUS_API_SECRET = os.environ.get("AMADEUS_API_SECRET", "Q2E3OAO8MRZoBHrj")

# Initialize LLM API client
try:
    llm_api = LLMApi()
    st.sidebar.success("Successfully connected to OpenAI API")
except ValueError as e:
    st.sidebar.error(f"Error initializing LLM API: {str(e)}")
    # Use a placeholder object so that the page can still load even if API initialization fails
    class DummyLLMApi:
        def process_travel_query(self, *args, **kwargs):
            return {"recommendations": "⚠️ Error: Could not connect to OpenAI API. Please check your API key in config.py."}
    llm_api = DummyLLMApi()

def get_amadeus_token():
    """Get OAuth2 token from Amadeus API"""
    url = "https://test.api.amadeus.com/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_API_KEY,
        "client_secret": AMADEUS_API_SECRET
    }
    
    # Make request to get the token
    response = requests.post(url, headers=headers, data=data)
    
    if response.status_code == 200:
        return response.json().get("access_token")
    else:
        st.error(f"Error getting Amadeus token: {response.text}")
        return None

def load_airport_data():
    """Load the airport dataset and prepare city-airport display format."""
    try:
        df = pd.read_csv("airports-code@public.csv", delimiter=";")
        df = df.rename(columns={"Airport Code": "IATA Code"})  # ensure consistency
        df["City-Airport"] = df["City Name"] + " (" + df["IATA Code"] + ")"
        return df
    except Exception as e:
        st.error(f"Error loading airport data: {e}")
        # Fallback if CSV fails
        data = {
            "City Name": ["New York", "Los Angeles", "London", "Paris", "Tokyo", "Sydney"],
            "IATA Code": ["JFK", "LAX", "LHR", "CDG", "HND", "SYD"]
        }
        df = pd.DataFrame(data)
        df["City-Airport"] = df["City Name"] + " (" + df["IATA Code"] + ")"
        return df


def get_airport_code(city_airport_str, airport_data):
    """Extract IATA code from formatted string 'City (IATA)'."""
    if "(" in city_airport_str and ")" in city_airport_str:
        return city_airport_str.split("(")[-1].replace(")", "").strip()
    return None


def get_flights(token, dep_iata, arr_iata, flight_date, return_date=None, adults=1, children=0, cabin_class="ECONOMY"):
    """Fetch flight offers from Amadeus API using IATA codes with full round-trip and traveler support."""
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }

    st.info(f"Searching flights from {dep_iata} to {arr_iata} on {flight_date}" +
            (f" and returning on {return_date}" if return_date else "") +
            f" | Class: {cabin_class} | Adults: {adults} | Children: {children}")

    params = {
        "originLocationCode": dep_iata,
        "destinationLocationCode": arr_iata,
        "departureDate": flight_date,
        "adults": adults,
        "children": children,
        "travelClass": cabin_class.upper().replace(" ", "_"),
        "max": 5,
        "currencyCode": "USD"
    }

    # Add return date if it's a round trip
    if return_date:
        params["returnDate"] = return_date

    try:
        response = requests.get(url, headers=headers, params=params)

        st.expander("API Request Details (for debugging)").write({
            "url": url,
            "params": params,
            "response_code": response.status_code
        })

        if response.status_code == 200:
            return response.json().get("data", [])
        else:
            error_message = response.text
            try:
                error_json = response.json()
                error_detail = error_json.get('errors', [{}])[0].get('detail', '')
                st.error(f"Error fetching flight data: {error_detail}")
            except:
                st.error(f"Error fetching flight data: {error_message}")
            return []
    except Exception as e:
        st.error(f"Exception while fetching flights: {str(e)}")
        return []


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

def process_flights_with_llm(flights, user_query):
    """Process flight data using LLM to create a formatted table and analysis"""
    if not flights:
        return "No flights found for the given search criteria."
    
    # If LLM API is unavailable or encounters an error, use backup analysis
    try:
        # Prepare user query
        llm_user_query = {
            "origin": user_query.get("origin", ""),
            "destination": user_query.get("destination", ""),
            "departure_date": user_query.get("departure_date", ""),
            "return_date": user_query.get("return_date", ""),
            "budget": user_query.get("budget", "medium"),
            "interests": user_query.get("interests", ["convenience", "value"])
        }
        
        # Display processing information
        st.info("Sending request to GPT-4o... (This may take a moment)")
        
        # Process request
        result = llm_api.process_travel_query(
            user_query=llm_user_query,
            flight_data=flights
        )
        
        # Get recommendation content
        recommendations = result.get("recommendations", "")
        
        # If there's no content, use backup analysis
        if not recommendations or "error" in recommendations:
            st.warning("AI service is currently limited. Using simplified analysis instead.")
            return analyze_flights_without_llm(flights, user_query)
        
        # Return recommendations
        return recommendations
    except Exception as e:
        st.error(f"Error processing with LLM: {str(e)}")
        st.info("Using basic flight analysis instead.")
        return analyze_flights_without_llm(flights, user_query)

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

def main():
    
    st.title("Flight Query Form ✈️")
    st.write("Fill in your flight details to receive personalized flight recommendations.")
    user_no = st.number_input("Please enter your user number:", min_value=0, step=1)

    # Check if there's session state
    if 'flight_options' not in st.session_state:
        st.session_state.flight_options = None
    
    if 'flight_analysis' not in st.session_state:
        st.session_state.flight_analysis = None
    
    if 'selected_flight' not in st.session_state:
        st.session_state.selected_flight = None
        
    # Store user ID in session state
    st.session_state.user_id = user_no

    # Load airport data
    airport_data = load_airport_data()
    
    if airport_data.empty:
        st.error("Could not load airport data. Please check the CSV file.")
        return
        
    # Add an empty option as default value
    city_options = [""] + sorted(airport_data["City-Airport"].dropna().unique())

    # Get today's date
    today = datetime.date.today()

    # Main flight search parameters
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_location = st.selectbox("Departure City", city_options, index=0)
    with col2:
        destination = st.selectbox("Destination City", city_options, index=0)
    with col3:
        start_date = st.date_input("Departure Date", min_value=today)
    with col4:
        end_date = st.date_input("Return Date", min_value=today)

    # Passenger and cabin details in a cleaner layout
    st.write("---")
    st.write("### Travel Details")
    
    col5, col6, col7 = st.columns(3)
    with col5:
        num_adults = st.number_input("Number of Adults", min_value=1, step=1)
        num_children = st.number_input("Number of Children", min_value=0, step=1)
    with col6:
        cabin_class = st.selectbox(
            "Cabin Class",
            ["Economy", "Premium Economy", "Business", "First Class"]
        )
    with col7:
        direct_flights_only = st.checkbox("Direct Flights Only")
        st.write("") # Add some spacing
        total_passengers = st.markdown(f"**Total Passengers:** {num_adults + num_children}")
        
    # Submit button
    if st.button("Search Flights"):
        if end_date < start_date:
            st.error("Return date must be the same as or after the departure date.")
            return
            
        # Check if both departure and destination cities are selected
        if not start_location or not destination:
            st.error("Please select both a departure and a destination city.")
            return
        
        # Check if departure and destination cities are the same
        if start_location == destination:
            st.error("Departure and destination cannot be the same city.")
            return
        
        # Get token
        with st.spinner("Authenticating with Amadeus API..."):
            token = get_amadeus_token()
            
        if not token:
            st.error("Failed to authenticate with Amadeus API.")
            return
        
        # Convert city names to IATA codes
        dep_iata = get_airport_code(start_location, airport_data)
        arr_iata = get_airport_code(destination, airport_data)

        if not dep_iata or not arr_iata:
            st.error("IATA code not found for the selected city. Try using direct IATA code input.")
            return

        # Format date for API
        formatted_date = start_date.strftime("%Y-%m-%d")
        formatted_end_date = end_date.strftime("%Y-%m-%d")

        # Fetch flight data using Amadeus API
        with st.spinner("Searching for flights..."):
            flights = get_flights(
                token,
                dep_iata,
                arr_iata,
                formatted_date,
                return_date=formatted_end_date,
                adults=num_adults,
                children=num_children,
                cabin_class=cabin_class
            )
        
        if flights:
            # Show raw API response in an expander (for debugging)
            with st.expander("API Response (Raw Data)"):
                st.json(flights)
            
            # Process flights with LLM and display formatted results
            st.subheader("Flight Analysis and Recommendations ✈️")
            
            # Prepare user query for LLM
            user_query = {
                "origin": start_location,
                "destination": destination,
                "departure_date": formatted_date,
                "return_date": formatted_end_date,
                "budget": "medium",  # Default value
                "interests": ["convenience", "value"],  # Default interests
                "user_id": user_no,
                "cabin_class": cabin_class,
                "adults": num_adults,
                "children": num_children,
                "direct_flights_only": direct_flights_only
            }
            
            # Save flight options to session state
            st.session_state.flight_options = flights
            
            # Save user query preferences to database
            save_query_preferences(user_query)
            
            with st.spinner("Analyzing flight options..."):
                llm_analysis = process_flights_with_llm(flights, user_query)
                st.session_state.flight_analysis = llm_analysis
                st.markdown(llm_analysis)
                
                # Display flight selection options
                display_flight_selection(flights, user_query)

            #preferences = collect_user_preferences()
        else:
            st.warning("No flights found for the given search criteria.")
    
    # If there's already flight analysis, display it
    elif st.session_state.flight_analysis:
        st.subheader("Flight Analysis and Recommendations ✈️")
        st.markdown(st.session_state.flight_analysis)
        
        # Display flight selection options
        if st.session_state.flight_options:
            display_flight_selection(st.session_state.flight_options, {
                "origin": start_location,
                "destination": destination,
                "user_id": user_no
            })

def collect_user_preferences():
    """Collect user preferences for travel planning"""
    st.write("---")
    st.subheader("Your Travel Preferences")
    
    # Create a dictionary to store preferences
    preferences = {}
    
    # Initialize session state for form persistence
    if 'activity_categories_selected' not in st.session_state:
        st.session_state.activity_categories_selected = []
    
    if 'hotel_price_level' not in st.session_state:
        st.session_state.hotel_price_level = "Medium"
        
    if 'cuisine_regions_selected' not in st.session_state:
        st.session_state.cuisine_regions_selected = ["Local Cuisine"]
    
    # Use a form to prevent page refresh on every interaction
    with st.form("Preferences Form"):
        # Activity Interests - Only keep main categories
        st.write("### Activity Interests")
        activity_categories = [
            "Cultural", 
            "Nature & Outdoors", 
            "Entertainment", 
            "Shopping", 
            "Recreation", 
            "Nightlife"
        ]
        
        selected_activity_categories = st.multiselect(
            "Select the types of activities you're interested in:",
            activity_categories,
            default=st.session_state.activity_categories_selected,
            key="activity_categories_widget"
        )
        
        # Hotel Preferences - Only keep price level
        st.write("### Hotel Preferences")
        
        # Price Level - Use English labels
        hotel_price_level = st.radio(
            "Preferred Hotel Price Level",
            options=["Budget", "Medium", "Luxury"],
            horizontal=True,
            key="hotel_price_widget",
            index=["Budget", "Medium", "Luxury"].index(st.session_state.hotel_price_level if st.session_state.hotel_price_level in ["Budget", "Medium", "Luxury"] else "Medium")
        )
        
        st.write("### Cuisine Preferences")
        # Cuisine regions - only show regions without detailed categories
        cuisine_regions = [
            "Asian", 
            "European", 
            "American/Latin", 
            "Middle Eastern",
            "African",
            "Caribbean",
            "Local Cuisine"
        ]
        
        selected_cuisine_regions = st.multiselect(
            "Select cuisine regions you're interested in:",
            cuisine_regions,
            default=st.session_state.cuisine_regions_selected,
            key="cuisine_regions_widget"
        )
        
        # Submit button for the form
        submitted = st.form_submit_button("Save Preferences")
        st.write(f"Selected activity categories: {selected_activity_categories}")
        if submitted:
            # Update session state values
            st.write(f"Selected activity categories: {selected_activity_categories}")
            st.session_state.activity_categories_selected = selected_activity_categories
            st.session_state.hotel_price_level = hotel_price_level
            st.session_state.cuisine_regions_selected = selected_cuisine_regions
    
    # If form was submitted, process the preferences
    if submitted or ('preferences_form' in st.session_state and st.session_state.preferences_form):
        # 整合旅行偏好信息为一个结构化的字典
        travel_preferences = {
            "activity_interests": selected_activity_categories,
            "hotel_preference": hotel_price_level,
            "cuisine_regions": selected_cuisine_regions
        }
        
        # 将旅行偏好添加到preferences字典中
        preferences["travel_preferences"] = travel_preferences
        
        # 也直接添加这些键，使DatabaseManager能够直接读取它们
        preferences["activity_interests"] = selected_activity_categories
        preferences["hotel_preference"] = hotel_price_level 
        preferences["cuisine_regions"] = selected_cuisine_regions
        
        # Save travel preferences to database if user_id is available
        if "user_id" in st.session_state:
            try:
                # Import database manager
                from database.db_manager import DatabaseManager
                
                # Create database manager instance
                db_manager = DatabaseManager()
                
                # Add timestamp
                preferences["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                preferences["user_id"] = st.session_state.user_id
                
                # Update temp.csv with user preferences
                user_id = str(st.session_state.user_id)
                result_file = db_manager.update_temp_with_preferences(user_id, preferences)
                
                if result_file and os.path.exists(result_file):
                    st.success("Your travel preferences have been saved successfully!")
                    
                    # 验证旅行偏好是否被成功保存
                    try:
                        df = pd.read_csv(result_file)
                        if 'user_preferences' in df.columns:
                            user_prefs = json.loads(df['user_preferences'].iloc[0])
                            if 'travel_preferences' in user_prefs:
                                st.sidebar.success("✓ Travel preferences verified in temp.csv")
                    except Exception as verify_err:
                        st.sidebar.error(f"Verification error: {str(verify_err)}")
                
            except Exception as e:
                st.error(f"Error saving travel preferences: {str(e)}")
                import traceback
                st.sidebar.error(f"Error details: {traceback.format_exc()}")
    else:
        # For initial load, use session state values
        preferences["activity_categories"] = st.session_state.activity_categories_selected
        preferences["hotel_price_level"] = st.session_state.hotel_price_level
        preferences["cuisine_regions"] = st.session_state.cuisine_regions_selected
        
        # Add API mappings for initial state as well
        activity_category_mapping = {
            "Cultural": ["museum", "art_gallery", "historical_landmark", "monument", "performing_arts_theater", "library", "cultural_center"],
            "Nature & Outdoors": ["park", "national_park", "state_park", "garden", "botanical_garden", "beach", "hiking_area", "trail_walking_path", "natural_feature", "mountain"],
            "Entertainment": ["amusement_park", "water_park", "movie_theater", "performing_arts_theater", "casino", "concert_hall"],
            "Shopping": ["shopping_mall", "market", "street_market", "department_store", "clothing_store", "specialty_food_shop", "gift_shop"],
            "Recreation": ["stadium", "sports_complex", "gym", "fitness_center", "swimming_pool", "golf_course", "spa"],
            "Nightlife": ["night_club", "bar", "pub", "lounge", "comedy_club"]
        }
        
        activity_api_types = []
        for category in st.session_state.activity_categories_selected:
            if category in activity_category_mapping:
                activity_api_types.extend(activity_category_mapping[category])
        
        preferences["activity_api_types"] = activity_api_types
        
        hotel_type_mapping = {
            "Budget": ["hostel", "motel", "campground", "guest_house", "lodge"],
            "Medium": ["hotel", "inn", "bed_and_breakfast", "resort"],
            "Luxury": ["hotel", "resort", "spa_resort", "luxury_hotel", "villa"]
        }
        preferences["hotel_types"] = hotel_type_mapping.get(st.session_state.hotel_price_level, ["hotel"])
    return preferences

def save_user_preferences(user_id, preferences, user_query, selected_flight):
    """Save user preferences and flight information to temp.csv"""
    try:
        from database.db_manager import DatabaseManager
        
        # Create database manager instance
        db_manager = DatabaseManager()
        
        # Add information prompt
        st.info("Processing and saving your travel preferences...")
        
        # Make sure user_id is a string
        user_id = str(user_id)
        
        # Add timestamp and user ID to preferences
        preferences["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        preferences["user_id"] = user_id
        
        # Add destination and trip dates
        preferences["destination"] = user_query.get("destination", "")
        preferences["departure_date"] = user_query.get("departure_date", "")
        preferences["return_date"] = user_query.get("return_date", "")
        
        # Debug print
        st.sidebar.text(f"User ID: {user_id}")
        st.sidebar.text(f"Database dir: {db_manager.database_dir}")
        
        # Get the user directory path
        user_dir = db_manager._get_user_dir(user_id)
        st.sidebar.text(f"User dir: {user_dir}")
        
        # Directly check if directory exists
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
            st.sidebar.text(f"Created user directory: {user_dir}")
        
        # Update temp.csv with user preferences - use the correct user_id parameter
        result_file = db_manager.update_temp_with_preferences(user_id, preferences)
        
        # Write preferences directly to file as fallback
        if not result_file or not os.path.exists(result_file):
            try:
                # Fallback: direct file writing
                st.sidebar.warning("Using fallback direct file writing")
                temp_file_path = os.path.join(user_dir, "temp.csv")
                
                # Check if file exists
                if os.path.exists(temp_file_path):
                    # Read existing file
                    try:
                        existing_df = pd.read_csv(temp_file_path)
                        existing_df["user_preferences"] = json.dumps(preferences)
                        existing_df.to_csv(temp_file_path, index=False)
                        result_file = temp_file_path
                        st.sidebar.success("✓ Direct update successful")
                    except Exception as direct_e:
                        st.sidebar.error(f"Direct update error: {str(direct_e)}")
                else:
                    # Create new file
                    df = pd.DataFrame([{
                        "timestamp": datetime.datetime.now().strftime("%Y%m%d_%H%M%S"),
                        "origin": user_query.get("origin", ""),
                        "destination": user_query.get("destination", ""),
                        "departure_date": user_query.get("departure_date", ""),
                        "return_date": user_query.get("return_date", ""),
                        "user_preferences": json.dumps(preferences)
                    }])
                    df.to_csv(temp_file_path, index=False)
                    result_file = temp_file_path
                    st.sidebar.success("✓ Direct file creation successful")
            except Exception as fallback_e:
                st.sidebar.error(f"Fallback error: {str(fallback_e)}")
        
        # Check if file was successfully updated
        if result_file and os.path.exists(result_file):
            st.success("Your preferences have been saved successfully!")
            
            # Verify the content
            try:
                df = pd.read_csv(result_file)
                if 'user_preferences' in df.columns:
                    st.sidebar.success(f"✓ Preferences stored in temp.csv")
                    return True
                else:
                    st.sidebar.warning("⚠ Preferences column not found in saved file")
                    return False
            except Exception as verify_err:
                st.sidebar.error(f"Verification error: {str(verify_err)}")
                return False
        else:
            st.error(f"Failed to save preferences. File path: {result_file}")
            return False
            
    except Exception as e:
        st.error(f"Error saving preferences: {str(e)}")
        import traceback
        st.sidebar.error(f"Stack trace: {traceback.format_exc()}")
        return False

def display_flight_selection(flights, user_query):
    """Display flight selection and handle user choice"""
    st.write("---")
    st.subheader("Choose Your Preferred Flight")
    st.session_state.selected_flight = None
    # Create selection widgets with index information
    flight_options = []
    for i, flight in enumerate(flights):
        airline = "Unknown Airline"
        price = "Unknown Price"
        
        # Extract basic flight information
        if "itineraries" in flight and flight["itineraries"]:
            if "segments" in flight["itineraries"][0] and flight["itineraries"][0]["segments"]:
                segment = flight["itineraries"][0]["segments"][0]
                if "carrierCode" in segment:
                    airline = segment["carrierCode"]
        
        if "price" in flight and "total" in flight["price"]:
            price = f"{flight['price']['total']} {flight['price'].get('currency', 'USD')}"
        
        option_label = f"Option {i+1} (Index: {i}): {airline} - {price}"
        flight_options.append(option_label)
    
    selected_index = st.selectbox("Select a flight", options=range(len(flight_options)), format_func=lambda x: flight_options[x])
    selected_flight = flights[selected_index] if selected_index < len(flights) else None
    
    # User feedback
    feedback = st.text_area("Your feedback on this flight (optional):", "")
    
    if st.button("Confirm Selection"):
        st.session_state.selected_flight = selected_flight
    # Confirm button
    if st.session_state.selected_flight:
            # Add flight index to user query
        user_query["selected_flight_index"] = selected_index
        
        # Save user selection - ensure user_id is available
        if "user_id" not in user_query or not user_query["user_id"]:
            user_query["user_id"] = "unknown"

        # add a debug print the selected flight json
        st.sidebar.text(f"Selected flight: {json.dumps(selected_flight, indent=4)}")
            
        save_success = save_user_selection(user_query, selected_flight, flights, feedback)
        
        if save_success:
            st.session_state.selected_flight = selected_flight
            st.success(f"You have selected {flight_options[selected_index]}. Your selection has been saved.")
            
            # Display details
            st.subheader("Your Selected Flight Details")
            
            # Extract and display key flight information
            if selected_flight:
                # Extract price information
                price = selected_flight.get('price', {})
                total_price = price.get('total', 'N/A')
                currency = price.get('currency', 'USD')
                
                # Display price
                st.write(f"**Total Price:** {total_price} {currency}")
                
                # Process itineraries
                itineraries = selected_flight.get('itineraries', [])
                for i, itinerary in enumerate(itineraries):
                    journey_type = "Outbound" if i == 0 else "Return"
                    st.write(f"\n**{journey_type} Journey:**")
                    
                    # Display duration
                    duration = itinerary.get('duration', 'N/A')
                    st.write(f"Duration: {duration}")
                    
                    # Process segments
                    segments = itinerary.get('segments', [])
                    st.write(f"Stops: {len(segments) - 1}")
                    
                    for segment in segments:
                        carrier = segment.get('carrierCode', 'N/A')
                        flight_number = segment.get('number', 'N/A')
                        
                        departure = segment.get('departure', {})
                        dep_time = departure.get('at', 'N/A')
                        dep_airport = departure.get('iataCode', 'N/A')
                        
                        arrival = segment.get('arrival', {})
                        arr_time = arrival.get('at', 'N/A')
                        arr_airport = arrival.get('iataCode', 'N/A')
                        
                        st.write(f"- Flight {carrier} {flight_number}")
                        st.write(f"  {dep_airport} → {arr_airport}")
                        st.write(f"  Departure: {dep_time}")
                        st.write(f"  Arrival: {arr_time}")
                
                # Display cabin and baggage information
                if 'travelerPricings' in selected_flight and selected_flight['travelerPricings']:
                    traveler = selected_flight['travelerPricings'][0]
                    if 'fareDetailsBySegment' in traveler and traveler['fareDetailsBySegment']:
                        segment = traveler['fareDetailsBySegment'][0]
                        cabin = segment.get('cabin', 'N/A')
                        included_baggage = segment.get('includedCheckedBags', {})
                        baggage_quantity = included_baggage.get('quantity', 0) if included_baggage else 0
                        
                        st.write(f"\n**Cabin Class:** {cabin}")
                        st.write(f"**Baggage Allowance:** {baggage_quantity} piece(s)")
                
                # Collect user preferences
    st.write("---")
    st.subheader("Tell Us About Your Travel Preferences")
    preferences = collect_user_preferences()
    
    # 使用收集到的旅行偏好，添加到现有的航班信息中
    if preferences and "travel_preferences" in preferences:
        # 获取用户ID
        user_id = user_query.get("user_id", "unknown")
        
        try:
            # 导入数据库管理器
            from database.db_manager import DatabaseManager
            
            # 创建数据库管理器实例
            db_manager = DatabaseManager()
            
            # 修复现有temp.csv文件
            fix_existing_temp_file(user_id)
            
            # 获取用户目录
            user_dir = db_manager._get_user_dir(user_id)
            temp_file_path = os.path.join(user_dir, "temp.csv")
            
            # 检查temp.csv是否存在
            if os.path.exists(temp_file_path):
                try:
                    # 读取现有的CSV文件
                    df = pd.read_csv(temp_file_path)
                    
                    # 检查是否有user_preferences列
                    if 'user_preferences' in df.columns:
                        # 解析现有的偏好数据
                        existing_prefs = json.loads(df['user_preferences'].iloc[0])
                        
                        # 添加或更新旅行偏好
                        existing_prefs["travel_preferences"] = preferences.get("travel_preferences")
                        
                        # 也直接添加单独的偏好字段，使其能够出现在CSV的单独列中
                        if "travel_preferences" in preferences and isinstance(preferences["travel_preferences"], dict):
                            travel_prefs = preferences["travel_preferences"]
                            if "activity_interests" in travel_prefs:
                                existing_prefs["activity_interests"] = travel_prefs["activity_interests"]
                            if "hotel_preference" in travel_prefs:
                                existing_prefs["hotel_preference"] = travel_prefs["hotel_preference"]
                            if "cuisine_regions" in travel_prefs:
                                existing_prefs["cuisine_regions"] = travel_prefs["cuisine_regions"]
                        
                        # 更新到CSV文件
                        df['user_preferences'] = json.dumps(existing_prefs)
                        df.to_csv(temp_file_path, index=False)
                        
                        st.sidebar.success("✓ Updated travel preferences in existing flight data")
                        st.success("Your travel preferences have been saved with your flight selection!")
                    else:
                        st.sidebar.warning("No user_preferences column found in temp.csv")
                except Exception as e:
                    st.sidebar.error(f"Error updating temp.csv: {str(e)}")
            else:
                st.sidebar.warning(f"temp.csv file not found at {temp_file_path}")
        except Exception as e:
            st.sidebar.error(f"Error processing travel preferences: {str(e)}")
        
        # Use a different key for this button
        if st.button("Generate Detailed Travel Plan", key="gen_plan_button"):
            st.info("Generating your travel plan, this may take a few minutes...")
            # Here we should call AI to generate detailed travel plan
            # Simulate progress bar
            progress_bar = st.progress(0)
            for percent_complete in range(100):
                time.sleep(0.05)
                progress_bar.progress(percent_complete + 1)
            
            st.success("Travel plan generated!")
            # Example travel plan content
            st.markdown("""
            ## Your Personalized Travel Plan
            
            ### Day 1
            - Morning: Arrive at destination, check-in to hotel
            - Afternoon: Visit main attractions
            - Evening: Enjoy local cuisine
            
            ### Day 2
            - Morning: Cultural experience activities
            - Afternoon: Shopping and free time
            - Evening: Local performance or entertainment
            
            ### Day 3
            - Morning: Day trip to nearby attractions
            - Evening: Return and rest
            
            ### Day 4
            - Morning: Prepare for return journey
            - Afternoon: Departure flight
            """)
            
            # Visualize recommended itinerary
            st.subheader("Budget Allocation")
            chart_data = pd.DataFrame({
                "Category": ["Transportation", "Accommodation", "Food", "Attractions", "Shopping"],
                "Budget Allocation": [30, 35, 15, 10, 10]
            })
            st.bar_chart(chart_data.set_index("Category"))


def save_user_selection(user_query, selected_flight, all_flights, user_feedback):
    """Save user selection to temp.csv file in user directory"""
    try:
        from database.db_manager import DatabaseManager
        
        # Add information prompt
        st.info("Processing flight data...")
        
        # Get user_id, use default if not available
        user_id = user_query.get("user_id", "unknown")
        if not user_id or user_id == "":
            user_id = "unknown"
            user_query["user_id"] = user_id
        
        st.sidebar.text(f"Processing selection for user: {user_id}")
        
        # 修复现有temp.csv文件
        fix_existing_temp_file(user_id)
        
        # Create database manager
        db_manager = DatabaseManager()
        
        # Let database manager handle flight data filtering and saving
        temp_file = db_manager.save_temp_data(user_query, selected_flight, all_flights)
        
        # Verify the temp file was created successfully
        if not temp_file or not os.path.exists(temp_file):
            st.sidebar.error(f"Failed to create temp file: {temp_file}")
            return False
        
        st.sidebar.success(f"Flight data saved to: {temp_file}")
        
        # 确保temp.csv文件包含user_preferences列
        try:
            df = pd.read_csv(temp_file)
            if "user_preferences" not in df.columns:
                st.sidebar.warning("Adding user_preferences column to temp.csv")
                df["user_preferences"] = json.dumps({})
                df.to_csv(temp_file, index=False)
        except Exception as e:
            st.sidebar.error(f"Error ensuring user_preferences column: {str(e)}")
        
        # Generate simulated travel plan for demonstration
        if selected_flight:
            # Use flight data
            essential_flight_info = {
                "flight_index": all_flights.index(selected_flight),
                "price": selected_flight.get('price', {}).get('total', 'N/A'),
                "currency": selected_flight.get('price', {}).get('currency', 'USD'),
                "cabin": selected_flight.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('cabin', 'N/A'),
                "baggage": selected_flight.get('travelerPricings', [{}])[0].get('fareDetailsBySegment', [{}])[0].get('includedCheckedBags', {}).get('quantity', 0),
                "segments": []
            }
            
            # Save only essential segment information
            for itinerary in selected_flight.get('itineraries', []):
                for segment in itinerary.get('segments', []):
                    essential_flight_info["segments"].append({
                        "carrier": segment.get('carrierCode', 'N/A'),
                        "flight_number": segment.get('number', 'N/A'),
                        "departure": {
                            "airport": segment.get('departure', {}).get('iataCode', 'N/A'),
                            "time": segment.get('departure', {}).get('at', 'N/A')
                        },
                        "arrival": {
                            "airport": segment.get('arrival', {}).get('iataCode', 'N/A'),
                            "time": segment.get('arrival', {}).get('at', 'N/A')
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
            
            # Save travel plan to recommendation file
            recommend_file = db_manager.save_recommendation(user_id, travel_plan, user_feedback)
            if recommend_file:
                st.sidebar.success(f"Travel plan saved to user recommendation database")
        
        st.sidebar.success(f"Session data saved to database")
        return True
    except Exception as e:
        st.sidebar.error(f"Error saving session data: {str(e)}")
        st.sidebar.error(f"Traceback: {traceback.format_exc()}")
        return False

def save_query_preferences(user_query):
    """
    Save user query preferences to the database temp.csv file
    
    Args:
        user_query: Dictionary containing user query information
    
    Returns:
        Boolean indicating success or failure
    """
    try:
        # Extract user_id from the query
        user_id = user_query.get("user_id", "unknown")
        
        # Make sure user_id is a string
        user_id = str(user_id)
        
        st.info("Saving your query preferences...")
        
        # Import database manager
        from database.db_manager import DatabaseManager
        
        # Create database manager instance
        db_manager = DatabaseManager()
        
        # Check and fix existing temp.csv file if needed
        fix_existing_temp_file(user_id)
        
        # Prepare preferences dictionary
        preferences = {
            "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "user_id": user_id,
            "origin": user_query.get("origin", ""),
            "destination": user_query.get("destination", ""),
            "departure_date": user_query.get("departure_date", ""),
            "return_date": user_query.get("return_date", ""),
            "budget": user_query.get("budget", "medium"),
            "interests": user_query.get("interests", []),
            "query_type": "flight_search"
        }
        
        # Add any additional parameters from user_query
        for key, value in user_query.items():
            if key not in preferences:
                preferences[key] = value
        
        # Get the user directory path
        user_dir = db_manager._get_user_dir(user_id)
        
        # Ensure directory exists
        if not os.path.exists(user_dir):
            os.makedirs(user_dir, exist_ok=True)
        
        # Update temp.csv with user preferences
        result_file = db_manager.update_temp_with_preferences(user_id, preferences)
        
        if result_file and os.path.exists(result_file):
            st.success("Successfully saved query preferences")
            return True
        else:
            st.error("Error saving query preferences")
            return False
            
    except Exception as e:
        st.error(f"Error saving query preferences: {str(e)}")
        import traceback
        st.sidebar.error(f"Error details: {traceback.format_exc()}")
        return False

def fix_existing_temp_file(user_id):
    """
    检查并修复现有的temp.csv文件，确保它包含user_preferences列
    
    Args:
        user_id: 用户ID
        
    Returns:
        None
    """
    try:
        # Import database manager
        from database.db_manager import DatabaseManager
        
        # Create database manager instance
        db_manager = DatabaseManager()
        
        # Get user directory path
        user_dir = db_manager._get_user_dir(user_id)
        temp_file_path = os.path.join(user_dir, "temp.csv")
        
        # Check if temp.csv file exists
        if os.path.exists(temp_file_path):
            try:
                # Read the CSV file
                df = pd.read_csv(temp_file_path)
                
                # Check if "user_preferences" column exists
                if "user_preferences" not in df.columns:
                    st.sidebar.warning(f"Fixing temp.csv for user {user_id}: adding user_preferences column")
                    
                    # Add empty user_preferences column
                    df["user_preferences"] = json.dumps({})
                    
                    # Save the updated file
                    df.to_csv(temp_file_path, index=False)
                    st.sidebar.success(f"Fixed temp.csv for user {user_id}")
            except Exception as e:
                st.sidebar.error(f"Error fixing temp.csv: {str(e)}")
    except Exception as e:
        st.sidebar.error(f"Error in fix_existing_temp_file: {str(e)}")

if __name__ == "__main__":
    main()