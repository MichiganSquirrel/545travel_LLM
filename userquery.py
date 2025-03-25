import streamlit as st
import pandas as pd
import datetime
import requests
import os

# Get API credentials from environment variables or set them directly
# Note: For better security, use environment variables instead of hardcoding
AMADEUS_API_KEY = os.environ.get("AMADEUS_API_KEY", "wnkJALiAYNo4duZVG88dgfI6H2jtGGG2")
AMADEUS_API_SECRET = os.environ.get("AMADEUS_API_SECRET", "Q2E3OAO8MRZoBHrj")

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
    """Load the airport dataset for city to airport code mapping."""
    try:
        df = pd.read_csv("airports-code@public.csv", delimiter=";")
        # Display a sample of the data for verification
        st.expander("Airport Data Sample (First 5 rows)").write(df.head())
        return df
    except Exception as e:
        st.error(f"Error loading airport data: {e}")
        # Create a fallback with common airports if the CSV fails to load
        data = {
            "City Name": ["New York", "Los Angeles", "London", "Paris", "Tokyo", "Sydney"],
            "Airport Code": ["JFK", "LAX", "LHR", "CDG", "HND", "SYD"]
        }
        return pd.DataFrame(data)

def get_airport_code(city, airport_data):
    """Retrieve the IATA airport code for a given city."""
    if airport_data.empty:
        return None
    
    # Try to find an exact match first
    match = airport_data[airport_data["City Name"].str.lower() == city.lower()]
    
    # Log what we found for debugging
    if not match.empty:
        code = match["Airport Code"].values[0]
        # Make sure the code is valid (3 letters)
        if code and isinstance(code, str) and len(code) == 3:
            return code.upper()  # Ensure the code is uppercase
    
    return None

def get_flights(token, dep_iata, arr_iata, flight_date, adults=1):
    """Fetch flight offers from Amadeus API using IATA codes."""
    url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    # Display the IATA codes being used
    st.info(f"Searching flights from {dep_iata} to {arr_iata} on {flight_date}")
    
    params = {
        "originLocationCode": dep_iata,
        "destinationLocationCode": arr_iata,
        "departureDate": flight_date,
        "adults": adults,
        "max": 10,
        "currencyCode": "USD"  # Adding explicit currency
    }
    
    try:
        response = requests.get(url, headers=headers, params=params)
        
        # Log the full request and response for debugging
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

def main():
    st.title("Flight Query Form ✈️")
    st.write("Fill in your flight details to receive personalized flight recommendations.")

    # Test token button
    if st.button("Test Amadeus Token"):
        token = get_amadeus_token()
        if token:
            st.success(f"Successfully obtained Amadeus token! Token starts with: {token[:10]}...")
        else:
            st.error("Failed to get Amadeus token. Check your API credentials.")

    # Load airport data
    airport_data = load_airport_data()
    
    if airport_data.empty:
        st.error("Could not load airport data. Please check the CSV file.")
        return
        
    city_options = ["Select a city"] + sorted(airport_data["City Name"].dropna().unique())

    # Get today's date
    today = datetime.date.today()

    # User inputs for flights
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_location = st.selectbox("Departure City", city_options, index=0)
    with col2:
        destination = st.selectbox("Destination City", city_options, index=0)
    with col3:
        start_date = st.date_input("Departure Date", min_value=today)
    with col4:
        end_date = st.date_input("Return Date", min_value=today)

    # Flight preferences
    col5, col6 = st.columns(2)
    with col5:
        flight_type = st.radio("Flight Type", ["One-way", "Round-trip"], horizontal=True)
    with col6:
        cabin_class = st.radio("Cabin Class", ["Economy", "Premium Economy", "Business", "First Class"], horizontal=True)

    # Direct flights and passenger count
    col7, col8, col9 = st.columns([2, 1, 1])
    with col7:
        direct_flights_only = st.checkbox("Direct Flights Only")
    with col8:
        num_adults = st.number_input("Number of Adults", min_value=1, step=1)
    with col9:
        num_children = st.number_input("Number of Children", min_value=0, step=1)

    # Add direct IATA code input option
    st.write("---")
    st.write("### Advanced: Enter IATA Codes Directly")
    st.write("If you're having trouble with city selection, you can enter airport codes directly:")
    
    col_iata1, col_iata2 = st.columns(2)
    with col_iata1:
        direct_dep_iata = st.text_input("Departure Airport Code (e.g., JFK, LAX)", "")
    with col_iata2:
        direct_arr_iata = st.text_input("Arrival Airport Code (e.g., LHR, CDG)", "")
    
    use_direct_codes = st.checkbox("Use direct IATA codes instead of city selection")
        
    # Submit button
    if st.button("Search Flights"):
        if end_date < start_date:
            st.error("Return date must be the same as or after the departure date.")
            return
            
        # Get token
        with st.spinner("Authenticating with Amadeus API..."):
            token = get_amadeus_token()
            
        if not token:
            st.error("Failed to authenticate with Amadeus API.")
            return
        
        # Determine which IATA codes to use
        if use_direct_codes:
            # Validate direct IATA codes
            if not direct_dep_iata or not direct_arr_iata:
                st.error("Please enter both departure and arrival IATA codes.")
                return
                
            if len(direct_dep_iata) != 3 or len(direct_arr_iata) != 3:
                st.error("IATA codes must be exactly 3 characters.")
                return
                
            dep_iata = direct_dep_iata.upper()
            arr_iata = direct_arr_iata.upper()
        else:
            # Use city-based selection
            if start_location == "Select a city" or destination == "Select a city":
                st.error("Please select both a departure and a destination city.")
                return
            if start_location == destination:
                st.error("Departure and destination cannot be the same city.")
                return
                
            # Convert city names to IATA codes
            dep_iata = get_airport_code(start_location, airport_data)
            arr_iata = get_airport_code(destination, airport_data)

            if not dep_iata or not arr_iata:
                st.error("IATA code not found for the selected city. Try using direct IATA code input.")
                return

        # Format date for API
        formatted_date = start_date.strftime("%Y-%m-%d")
        
        # Fetch flight data using Amadeus API
        with st.spinner("Searching for flights..."):
            flights = get_flights(token, dep_iata, arr_iata, formatted_date)
        
        if flights:
            st.subheader("Available Flights ✈️")
            for flight in flights:
                # Extract and display flight information
                itineraries = flight.get("itineraries", [])
                if not itineraries:
                    continue
                    
                for idx, itinerary in enumerate(itineraries):
                    segments = itinerary.get("segments", [])
                    if not segments:
                        continue
                        
                    st.write(f"### Option {idx + 1}")
                    st.write(f"**Price:** {flight.get('price', {}).get('total')} {flight.get('price', {}).get('currency', 'EUR')}")
                    
                    for segment_idx, segment in enumerate(segments):
                        departure = segment.get("departure", {})
                        arrival = segment.get("arrival", {})
                        carrier_code = segment.get("carrierCode", "N/A")
                        flight_number = segment.get("number", "N/A")
                        
                        st.write(f"**Segment {segment_idx + 1}**")
                        st.write(f"🛫 **Departure:** {departure.get('iataCode', 'N/A')} at {format_datetime(departure.get('at'))}")
                        st.write(f"🛬 **Arrival:** {arrival.get('iataCode', 'N/A')} at {format_datetime(arrival.get('at'))}")
                        st.write(f"✈️ **Flight:** {carrier_code} {flight_number}")
                    
                    st.write("---")
        else:
            st.warning("No flights found for the given search criteria.")

if __name__ == "__main__":
    main()