# API Configuration File
# Fill in your API keys below

# OpenAI API Configuration
OPENAI_API_KEY = ""  # Your OpenAI API key for GPT-4o

# Anthropic API Configuration
ANTHROPIC_API_KEY = ""  # Your Anthropic API key

# Amadeus API Configuration
AMADEUS_API_KEY = "wnkJALiAYNo4duZVG88dgfI6H2jtGGG2"  # Your Amadeus API key
AMADEUS_API_SECRET = "Q2E3OAO8MRZoBHrj"  # Your Amadeus API secret

# Google Places API Configuration
GOOGLE_PLACES_API_KEY = "AIzaSyAxDNWWUNd0w7K_v4LZLI51Peu9aelBWp8"  # Your Google Places API key

# Other API keys can be added here as needed
# ...

# Load environment variables from this file
def load_api_keys():
    """Load API keys as environment variables"""
    import os
    
    # Set OpenAI API key
    if OPENAI_API_KEY:
        os.environ["OPENAI_API_KEY"] = OPENAI_API_KEY
    else:
        # Ensure API key format is correct (remove possible spaces or line breaks)
        api_key = "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"
        api_key = api_key.strip()  # Remove spaces
        os.environ["OPENAI_API_KEY"] = api_key
        print(f"Using default OpenAI API key: {api_key[:10]}...")
    
    # Set Anthropic API key
    if ANTHROPIC_API_KEY:
        os.environ["ANTHROPIC_API_KEY"] = ANTHROPIC_API_KEY
    
    # Set Amadeus API keys
    if AMADEUS_API_KEY:
        os.environ["AMADEUS_API_KEY"] = AMADEUS_API_KEY
    if AMADEUS_API_SECRET:
        os.environ["AMADEUS_API_SECRET"] = AMADEUS_API_SECRET
        
    # Set Google Places API key
    if GOOGLE_PLACES_API_KEY:
        os.environ["GOOGLE_PLACES_API_KEY"] = GOOGLE_PLACES_API_KEY

# Add this to your main.py or app startup
if __name__ == "__main__":
    load_api_keys() 