import requests
import os
from config import load_api_keys

class AmadeusAPI:
    def __init__(self):
        load_api_keys()
        self.AMADEUS_API_KEY = os.environ.get("AMADEUS_API_KEY", "wnkJALiAYNo4duZVG88dgfI6H2jtGGG2")
        self.AMADEUS_API_SECRET = os.environ.get("AMADEUS_API_SECRET", "Q2E3OAO8MRZoBHrj")
    
    def get_amadeus_token(self):
        """Get OAuth2 token from Amadeus API"""
        url = "https://test.api.amadeus.com/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.AMADEUS_API_KEY,
            "client_secret": self.AMADEUS_API_SECRET
        }
        # Make request to get the token
        response = requests.post(url, headers=headers, data=data)
        
        if response.status_code == 200:
            return response.json().get("access_token")
        else:
            raise Exception("Error: Amadeus token unable to get")
    
    def get_flights(self, token, dep_iata, arr_iata, flight_date, return_date=None, adults=1, children=0, cabin_class="ECONOMY"):
        """Fetch flight offers from Amadeus API using IATA codes with full round-trip and traveler support."""
        url = "https://test.api.amadeus.com/v2/shopping/flight-offers"
        
        headers = {
            "Authorization": f"Bearer {token}"
        }
        """
        st.info(f"Searching flights from {dep_iata} to {arr_iata} on {flight_date}" +
                (f" and returning on {return_date}" if return_date else "") +
                f" | Class: {cabin_class} | Adults: {adults} | Children: {children}")
        """
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
            
            print({
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
                    raise Exception(f"Error fetching flight data: {error_detail}")
                except:
                    raise Exception(f"Error fetching flight data: {error_message}")
        except Exception as e:
            raise Exception(f"Exception while fetching flights: {str(e)}")