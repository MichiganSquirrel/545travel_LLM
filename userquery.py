import streamlit as st
import pandas as pd
import datetime
import requests
import os
import json
import sys
import re

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入配置和API
from config import load_api_keys
from api.llm_api import LLMApi

# 首先加载API密钥
load_api_keys()

# Get API credentials from environment variables or set them directly
# Note: For better security, use environment variables instead of hardcoding
AMADEUS_API_KEY = os.environ.get("AMADEUS_API_KEY", "wnkJALiAYNo4duZVG88dgfI6H2jtGGG2")
AMADEUS_API_SECRET = os.environ.get("AMADEUS_API_SECRET", "Q2E3OAO8MRZoBHrj")

# 初始化LLM API客户端
try:
    llm_api = LLMApi()
    st.sidebar.success("Successfully connected to OpenAI API")
except ValueError as e:
    st.sidebar.error(f"Error initializing LLM API: {str(e)}")
    # 使用一个占位符对象，这样即使API初始化失败，页面也能加载
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
    
    # 如果LLM API不可用或出错，使用备用分析
    try:
        # 准备用户查询
        llm_user_query = {
            "origin": user_query.get("origin", ""),
            "destination": user_query.get("destination", ""),
            "departure_date": user_query.get("departure_date", ""),
            "return_date": user_query.get("return_date", ""),
            "budget": user_query.get("budget", "medium"),
            "interests": user_query.get("interests", ["convenience", "value"])
        }
        
        # 显示正在处理的信息
        st.info("Sending request to GPT-4o... (This may take a moment)")
        
        # 处理请求
        result = llm_api.process_travel_query(
            user_query=llm_user_query,
            flight_data=flights
        )
        
        # 获取推荐内容
        recommendations = result.get("recommendations", "")
        
        # 如果没有内容，使用备用分析
        if not recommendations or "error" in recommendations:
            st.warning("AI service is currently limited. Using simplified analysis instead.")
            return analyze_flights_without_llm(flights, user_query)
        
        # 返回推荐内容
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

    # 检查是否有会话状态
    if 'flight_options' not in st.session_state:
        st.session_state.flight_options = None
    
    if 'flight_analysis' not in st.session_state:
        st.session_state.flight_analysis = None
    
    if 'selected_flight' not in st.session_state:
        st.session_state.selected_flight = None

    # Load airport data
    airport_data = load_airport_data()
    
    if airport_data.empty:
        st.error("Could not load airport data. Please check the CSV file.")
        return
        
    # 添加一个空选项作为默认值
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
            
        # 检查是否选择了出发地和目的地
        if not start_location or not destination:
            st.error("Please select both a departure and a destination city.")
            return
        
        # 检查出发地和目的地是否相同
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
                "user_id": user_no
            }
            
            # 保存航班选项到会话状态
            st.session_state.flight_options = flights
            
            with st.spinner("Analyzing flight options..."):
                llm_analysis = process_flights_with_llm(flights, user_query)
                st.session_state.flight_analysis = llm_analysis
                st.markdown(llm_analysis)
                
                # 显示航班选择选项
                display_flight_selection(flights, user_query)
        else:
            st.warning("No flights found for the given search criteria.")
    
    # 如果已经有航班分析，显示它
    elif st.session_state.flight_analysis:
        st.subheader("Flight Analysis and Recommendations ✈️")
        st.markdown(st.session_state.flight_analysis)
        
        # 显示航班选择选项
        if st.session_state.flight_options:
            display_flight_selection(st.session_state.flight_options, {
                "origin": start_location,
                "destination": destination,
                "user_id": user_no
            })

def display_flight_selection(flights, user_query):
    """显示航班选择界面"""
    st.write("---")
    st.subheader("Select Your Preferred Flight ✈️")
    
    # 创建选项列表
    flight_options = []
    for i, flight in enumerate(flights[:5], 1):
        price = flight.get('price', {}).get('total', 'N/A')
        currency = flight.get('price', {}).get('currency', 'EUR')
        
        # 提取航空公司信息
        airlines = []
        for itinerary in flight.get('itineraries', []):
            for segment in itinerary.get('segments', []):
                airline = segment.get('carrierCode', 'Unknown')
                if airline not in airlines:
                    airlines.append(airline)
        
        airline_str = ", ".join(airlines)
        option_text = f"Option {i}: {airline_str} - {price} {currency}"
        flight_options.append(option_text)
    
    # 添加一个"不确定"选项
    flight_options.append("I need more information before deciding")
    
    # 创建选择框
    selected_option = st.radio("Which flight option would you like to book?", flight_options)
    
    # 创建文本输入框，让用户提供更多信息（非必填）
    user_feedback = st.text_area("Additional comments or requirements (optional):", "")
    
    # 提交按钮
    if st.button("Confirm Selection"):
        if selected_option == "I need more information before deciding":
            if not user_feedback:
                st.error("Please provide details about what additional information you need.")
            else:
                # 保存用户反馈
                st.info(f"Thank you for your feedback. We'll provide more information about: {user_feedback}")
                save_user_selection(user_query, None, flights, user_feedback)
        else:
            # 提取选择的航班索引
            selected_index = int(selected_option.split(":")[0].replace("Option ", "")) - 1
            selected_flight = flights[selected_index]
            
            # 保存用户选择
            save_user_selection(user_query, selected_flight, flights, user_feedback)
            
            # 显示确认信息
            st.success(f"You've selected {selected_option}!")
            st.info("Your selection has been saved. Thank you for using our service!")
            
            # 显示选定航班的详细信息
            display_selected_flight_details(selected_flight)

def display_selected_flight_details(flight):
    """显示选定航班的详细信息"""
    st.write("---")
    st.subheader("Your Selected Flight Details")
    
    price = flight.get('price', {}).get('total', 'N/A')
    currency = flight.get('price', {}).get('currency', 'EUR')
    
    st.write(f"**Price:** {price} {currency}")
    
    # 显示行程详情
    st.write("#### Itinerary Details:")
    
    for i, itinerary in enumerate(flight.get('itineraries', [])):
        st.write(f"**{'Outbound' if i == 0 else 'Return'} Journey:**")
        
        for j, segment in enumerate(itinerary.get('segments', [])):
            departure = segment.get('departure', {})
            arrival = segment.get('arrival', {})
            carrier = segment.get('carrierCode', 'N/A')
            flight_number = segment.get('number', 'N/A')
            
            dep_time = format_datetime(departure.get('at', 'N/A'))
            arr_time = format_datetime(arrival.get('at', 'N/A'))
            dep_airport = departure.get('iataCode', 'N/A')
            arr_airport = arrival.get('iataCode', 'N/A')
            
            st.write(f"Segment {j+1}: {carrier} {flight_number}")
            st.write(f"From: {dep_airport} at {dep_time}")
            st.write(f"To: {arr_airport} at {arr_time}")
            st.write("---")

def save_user_selection(user_query, selected_flight, all_flights, user_feedback):
    """保存用户选择到CSV文件"""
    # 创建database目录（如果不存在）
    database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
    os.makedirs(database_dir, exist_ok=True)
    
    # 创建唯一的文件名
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    user_id = user_query.get("user_id", "unknown")
    filename = os.path.join(database_dir, f"session_{user_id}_{timestamp}.csv")
    
    # 准备会话数据
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
    
    # 将数据写入CSV文件
    try:
        df = pd.DataFrame([session_data])
        df.to_csv(filename, index=False)
        st.sidebar.success(f"Session data saved to database")
    except Exception as e:
        st.sidebar.error(f"Error saving session data: {str(e)}")

if __name__ == "__main__":
    main()