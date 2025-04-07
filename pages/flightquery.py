import streamlit as st
import sys
sys.path.append("..")
from utils import load_airport_data, get_airport_code, fix_existing_temp_file, save_user_selection, format_duration, format_time
from api.flight_api import AmadeusAPI
from api.llm_api import LLMApi
import datetime
from database.db_manager import DatabaseManager
import os


def process_flights_with_llm(flights, user_query):
    """Process flight data using LLM to create a formatted table and analysis"""
    llm_api = LLMApi()
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
        #st.info("Sending request to GPT-4o... (This may take a moment)")
        
        # Process request
        result = llm_api.process_travel_query(
            user_query=llm_user_query,
            flight_data=flights
        )
        
        # Get recommendation content
        recommendations = result.get("recommendations", "")
        
        # If there's no content, use backup analysis
        if not recommendations or "error" in recommendations:
            st.warning("AI service is currently limited.")
            return "Error: AI cannot be used"
        return recommendations
    except Exception as e:
        st.error(f"Error processing with LLM: {str(e)}")
        #st.info("Using basic flight analysis instead.")
        return "Error: AI cannot be used"

st.set_page_config(
        page_title="Flight Search",
        page_icon="✈️",
        initial_sidebar_state='collapsed'
    )
st.title("EECS 545 Travel Planner 🌏")
st.logo("images/TravelPlanner_Logo.png", icon_image="images/TravelPlanner_Logo.png")
st.subheader("Flight Query Form ✈️")
if "user_no" not in st.session_state or st.session_state.user_no==None:
    st.error("Please login first to check flights")
    if st.button("Login", type="primary"):
        st.switch_page("app.py")
else:
    st.write("Fill in your flight details to receive personalized flight recommendations.")

    # Initialize the Flights API
    Amadeus = AmadeusAPI()

    # Check if there's session state
    if 'user_no' not in st.session_state:
        st.session_state.user_no = None

    if 'flight_options' not in st.session_state:
        st.session_state.flight_options = None

    if 'flight_analysis' not in st.session_state:
        st.session_state.flight_analysis = None

    if 'selected_flight' not in st.session_state:
        st.session_state.selected_flight = None

    if 'user_query' not in st.session_state:
        st.session_state.user_query = None
    
    # Load airport data
    airport_data = load_airport_data()

    if airport_data.empty:
        st.error("Could not load airport data. Please check the CSV file.")
        
    # Add an empty option as default value
    city_options = sorted(airport_data["City-Airport"].dropna().unique())

    # Get today's date
    today = datetime.date.today()

    #if not st.session_state.departure_city or not st.session_state.destination:
        # Main flight search parameters
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            start_location = st.selectbox("Departure City", city_options, index=None)
        with col2:
            destination = st.selectbox("Destination City", city_options, index=None)
        with col3:
            start_date = st.date_input("Departure Date", min_value=today, value=None)
        with col4:
            end_date = st.date_input("Return Date", min_value=today, value=None)

        col5, col6, _, col7 = st.columns([1,1,1,2])
        with col5:
            num_adults = st.number_input("Adults", min_value=1, step=1)
        with col6:
            num_children = st.number_input("Children", min_value=0, step=1)
        with col7:
            cabin_class = st.selectbox(
                "Cabin Class",
                ["Economy", "Premium Economy", "Business", "First Class"]
            )
    # Submit button
    if st.button("Search Flights",type="primary"):
        if end_date < start_date:
            st.error("Return date must be the same as or after the departure date.")  
        # Check if both departure and destination cities are selected
        if not start_location or not destination:
            st.error("Please select both a departure and a destination city.")
        # Check if start and end dates are selected
        if not start_date or not end_date:
            st.error("Please select a departure date and a return date")
        # Check if departure and destination cities are the same
        if start_location == destination:
            st.error("Departure and destination cannot be the same city.")
        # Get token
        with st.spinner("Authenticating with Amadeus API..."):
            token = Amadeus.get_amadeus_token()
        if not token:
            st.error("Failed to authenticate with Amadeus API.")
        
        # Convert city names to IATA codes
        dep_iata = get_airport_code(start_location)
        arr_iata = get_airport_code(destination)

        if not dep_iata or not arr_iata:
            st.error("IATA code not found for the selected city. Try using direct IATA code input.")
        
        # Format date for API
        formatted_date = start_date.strftime("%Y-%m-%d")
        formatted_end_date = end_date.strftime("%Y-%m-%d")

        # Fetch flight data using Amadeus API
        with st.spinner("Searching for flights..."):
            flights = Amadeus.get_flights(
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
            # Prepare user query for LLM
            user_query = {
                "origin": start_location,
                "destination": destination,
                "departure_date": formatted_date,
                "return_date": formatted_end_date,
                "budget": "medium",  # Default value
                "interests": ["convenience", "value"],  # Default interests
                "user_id": st.session_state.user_no,
                "cabin_class": cabin_class,
                "adults": num_adults,
                "children": num_children,
                "direct_flights_only": False
            }
            # Save flight options to session state
            st.session_state.flight_options = flights
            
            try:
                # Make sure user_id is a string
                user_id = str(st.session_state.user_no)
                #st.info("Saving your query preferences...")
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
                result_file,initial_data = db_manager.update_temp_with_preferences(user_id, preferences)
                
                if result_file and os.path.exists(result_file):
                    st.success("Successfully saved query preferences")
                else:
                    st.error("Error saving query preferences")
                
            except Exception as e:
                st.error(f"Error saving query preferences: {str(e)}")
                import traceback
                st.sidebar.error(f"Error details: {traceback.format_exc()}")

            with st.spinner("Analyzing flight options..."):
                llm_analysis = process_flights_with_llm(flights, user_query)
                st.session_state.user_query = user_query
                st.session_state.flight_analysis = llm_analysis
                # st.write("---")
                # st.markdown(llm_analysis)
                st.rerun()
        else:
            st.warning("No flights found for the given search criteria.")

    # If there's already flight analysis, display it
    elif st.session_state.flight_analysis:
        #st.subheader("Flight Analysis and Recommendations ✈️")
        st.markdown(st.session_state.flight_analysis)
        
        # Display flight selection options
        if st.session_state.flight_options:
            from datetime import datetime

            st.write("---")
            st.subheader("✈️ Choose Your Preferred Flight")
            st.session_state.selected_flight = None

            def format_time(iso_str):
                try:
                    return datetime.fromisoformat(iso_str).strftime("%H:%M, %b %d")
                except:
                    return "Unknown Time"

            # Prepare flight option descriptions
            flight_options = []
            for i, flight in enumerate(st.session_state.flight_options):
                airline = "Unknown Airline"
                price = "Unknown Price"
                departure = arrival = "N/A"
                stops = 0

                if flight.get("itineraries"):
                    segments = flight["itineraries"][0].get("segments", [])
                    if segments:
                        first_seg = segments[0]
                        last_seg = segments[-1]
                        departure = f"{first_seg.get('departure', {}).get('iataCode', '???')} at {format_time(first_seg.get('departure', {}).get('at', ''))}"
                        arrival = f"{last_seg.get('arrival', {}).get('iataCode', '???')} at {format_time(last_seg.get('arrival', {}).get('at', ''))}"
                        stops = len(segments) - 1
                        airline = first_seg.get("carrierCode", "Unknown Airline")

                if "price" in flight and "total" in flight["price"]:
                    price = f"{flight['price']['total']} {flight['price'].get('currency', 'USD')}"

                option_str = (
                    f"✈️ Option {i+1}: {airline} | {price}    \n"
                    f"🕘 {departure} ➡️ {arrival}\n"
                )
                flight_options.append(option_str)

            # Display selection
            selected_index = st.selectbox(
                "Select a flight below:",
                options=range(len(flight_options)),
                format_func=lambda x: flight_options[x]
            )
            # Feedback
            feedback = st.text_area("💬 Any feedback on this flight?", placeholder="Tell us what you think (optional)")
            if st.button("Confirm Selection", type="primary"):
                st.session_state.selected_flight = st.session_state.flight_options[selected_index]
                st.session_state.user_query["selected_flight_index"] = selected_index
                save_success, tempdata = save_user_selection(st.session_state.user_query, st.session_state.selected_flight, st.session_state.flight_options, feedback)
                if tempdata:
                    st.session_state['tempdata'] = tempdata
                if save_success:
                    st.success(f"You have selected {flight_options[selected_index]}.\n Your selection has been saved.")
                    
                    # Display details
                    st.subheader("✈️ Your Selected Flight Details")

                    # Check if flight is selected
                    if st.session_state.selected_flight:
                        flight = st.session_state.selected_flight

                        # Extract and display price information
                        price = flight.get('price', {})
                        total_price = price.get('total', 'N/A')
                        currency = price.get('currency', 'USD')
                        st.markdown(f"---\n### 💰 Total Price: `{total_price} {currency}`")
                        
                        col1, col2 = st.columns(2)
                        # Display itinerary details
                        itineraries = flight.get('itineraries', [])
                        for i, itinerary in enumerate(itineraries):
                            journey_type = "🛫 Outbound" if i == 0 else "🛬 Return"
                            col = col1 if i==0 else col2
                            with col:
                                st.markdown(f"### {journey_type}")
                                # Duration and stops
                                duration = format_duration(itinerary.get('duration', 'N/A'))
                                segments = itinerary.get('segments', [])
                                num_stops = len(segments) - 1

                                st.markdown(f"""
                                <div style="padding: 10px; border-left: 4px solid #4CAF50; background-color: #f9f9f9;">
                                    <strong>Duration:</strong> {duration}<br>
                                    <strong>Stops:</strong> {num_stops}
                                </div>
                                """, unsafe_allow_html=True)

                                # Segment details
                                for seg_num, segment in enumerate(segments, start=1):
                                    carrier = segment.get('carrierCode', 'N/A')
                                    flight_number = segment.get('number', 'N/A')

                                    departure = segment.get('departure', {})
                                    dep_time = format_time(departure.get('at', 'N/A'))
                                    dep_airport = departure.get('iataCode', 'N/A')

                                    arrival = segment.get('arrival', {})
                                    arr_time = format_time(arrival.get('at', 'N/A'))
                                    arr_airport = arrival.get('iataCode', 'N/A')

                                    st.markdown(f"""
                                    <div style="margin-top: 20px; padding: 16px; border-radius: 12px; border: 1px solid #e0e0e0; box-shadow: 0 2px 5px rgba(0,0,0,0.05); background-color: #ffffff;">
                                        <h4 style="margin-bottom: 12px; font-size: 20px; color: #333;">✈️ Segment {seg_num}</h4>
                                        <div style="line-height: 1.8; font-size: 16px; color: #555;">
                                            <p><strong>Flight:</strong> {carrier} {flight_number}</p>
                                            <p><strong>Route:</strong> {dep_airport} → {arr_airport}</p>
                                            <p><strong>Departure:</strong> {dep_time}</p>
                                            <p><strong>Arrival:</strong> {arr_time}</p>
                                        </div>
                                    </div>
                                    """, unsafe_allow_html=True)



                        # Display cabin and baggage information
                        st.markdown("---\n### 🧳 Additional Details")
                        traveler_pricings = flight.get('travelerPricings', [])
                        if traveler_pricings:
                            traveler = traveler_pricings[0]
                            fare_details = traveler.get('fareDetailsBySegment', [])
                            if fare_details:
                                segment_details = fare_details[0]
                                cabin = segment_details.get('cabin', 'N/A')
                                baggage_info = segment_details.get('includedCheckedBags', {})
                                baggage_quantity = baggage_info.get('quantity', 0) if baggage_info else 0

                                st.markdown(f"- **Cabin Class:** `{cabin}`")
                                st.markdown(f"- **Checked Baggage Allowance:** `{baggage_quantity} piece(s)`")

            if st.button("Edit Travel Preferences", type="secondary"):
                st.switch_page("pages/preferences.py")

