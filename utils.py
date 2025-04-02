import datetime
import pandas as pd


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


def get_airport_code(city_airport_str, airport_data):
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