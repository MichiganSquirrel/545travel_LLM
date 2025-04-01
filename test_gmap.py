import os
import requests
import json

# Set your API key securely (for example, using environment variables)
api_key = os.environ.get('GOOGLE_MAPS_API_KEY')
url = "https://places.googleapis.com/v1/places:searchNearby"

# Define headers with the API key and desired field mask
headers = {
    "Content-Type": "application/json",
    "X-Goog-Api-Key": api_key,
    "X-Goog-FieldMask": "places.displayName,places.formattedAddress,places.types"
}

# Build the JSON payload
payload = {
    "includedPrimaryTypes": ["restaurant"],
    "maxResultCount": 10,
    "locationRestriction": {
        "circle": {
            "center": {"latitude": 37.7937, "longitude": -122.3965},
            "radius": 500.0
        }
    }
}

# Send the POST request
response = requests.post(url, headers=headers, data=json.dumps(payload))

# Process the response
if response.status_code == 200:
    results = response.json()
    print("Search Results:", results)
else:
    print("Error:", response.status_code, response.text)
