import streamlit as st
import pandas as pd
import datetime
import requests
import os

# Replace this with your actual API key
API_KEY = os.getenv("AVIATION_STACK_API_KEY")

def load_airport_data():
    """Load the airport dataset for city to airport code mapping."""
    df = pd.read_csv("airports-code@public.csv", delimiter=";")
    return df

def get_airport_code(city, airport_data):
    """Retrieve the IATA airport code for a given city."""
    match = airport_data[airport_data["City Name"].str.lower() == city.lower()]
    return match["Airport Code"].values[0] if not match.empty else None

def get_flights(dep_iata, arr_iata, flight_date):
    """Fetch flight data from Aviationstack API using IATA codes."""
    url = "http://api.aviationstack.com/v1/flights"
    params = {
        "access_key": API_KEY,
        "dep_iata": dep_iata,
        "arr_iata": arr_iata,
        "flight_date": flight_date,
        "limit": 10
    }
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        return response.json().get("data", [])
    else:
        st.error("Error fetching flight data.")
        return []

def main():
    st.title("Flight Query Form ✈️")
    st.write("Fill in your flight details to receive personalized flight recommendations.")

    # Load airport data
    airport_data = load_airport_data()
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

    # Submit button
    if st.button("Search Flights"):
        if end_date < start_date:
            st.error("Return date must be the same as or after the departure date.")
            return
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
            st.error("IATA code not found for the selected city. Try another city.")
            return

        # Fetch flight data using IATA codes
        flights = get_flights(dep_iata, arr_iata, str(start_date))
        
        if flights:
            st.subheader("Available Flights ✈️")
            for flight in flights:
                st.write(f"**Flight Number:** {flight['flight']['iata']} ({flight['airline']['name']})")
                st.write(f"🛫 **Departure:** {flight['departure']['airport']} ({flight['departure']['iata']}) at {flight['departure']['scheduled']}")
                st.write(f"🛬 **Arrival:** {flight['arrival']['airport']} ({flight['arrival']['iata']}) at {flight['arrival']['scheduled']}")
                st.write(f"🕒 **Status:** {flight['flight_status']}")
                st.write("---")
        else:
            st.warning("No flights found for the given search criteria.")

if __name__ == "__main__":
    main()
