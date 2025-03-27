import os
import requests
import json
import time
import logging
from typing import Dict, List, Any, Optional

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_api")

class LLMApi:
    """API client for interacting with OpenAI's GPT-4o model"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "gpt-4o"):
        """
        Initialize the LLM API client
        
        Args:
            api_key: API key for OpenAI (defaults to environment variable)
            model: Model name to use (default: gpt-4o)
        """
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as OPENAI_API_KEY environment variable")
        
        # 记录API密钥的前10个字符（用于调试）
        logger.info(f"Initialized LLM API with key starting with: {self.api_key[:10]}...")
        
        self.model = model
        self.base_url = "https://api.openai.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 验证API密钥
        self._validate_api_key()
    
    def _validate_api_key(self):
        """验证API密钥是否有效"""
        try:
            # 发送一个简单的请求来验证API密钥
            test_prompt = "Hello, this is a test."
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": [{"role": "user", "content": test_prompt}],
                "max_tokens": 10
            }
            
            logger.info("Validating API key with a test request...")
            response = requests.post(url, headers=self.headers, json=payload)
            
            if response.status_code == 200:
                logger.info("API key validation successful!")
            else:
                logger.error(f"API key validation failed with status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
        except Exception as e:
            logger.error(f"Error validating API key: {str(e)}")
    
    def generate_text(self, prompt: str, max_tokens: int = 4000, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate text using GPT-4o
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
            
        Returns:
            Dictionary containing the model's response
        """
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        logger.info(f"Sending request to OpenAI API: {url}")
        logger.info(f"Using model: {self.model}")
        
        try:
            # 打印请求信息（不包含完整提示词，以避免日志过大）
            logger.info(f"Request payload: {json.dumps({k: v if k != 'messages' else '[PROMPT_CONTENT]' for k, v in payload.items()})}")
            
            # 发送请求
            response = requests.post(url, headers=self.headers, json=payload, timeout=60)
            
            # 记录响应状态
            logger.info(f"Response status code: {response.status_code}")
            
            # 检查是否成功
            if response.status_code != 200:
                logger.error(f"API error: {response.status_code} - {response.text}")
                return {"error": f"API error: {response.status_code} - {response.text}"}
            
            # 解析JSON响应
            json_response = response.json()
            logger.info("Successfully received response from OpenAI API")
            
            return json_response
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {str(e)}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response content: {e.response.text}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            return {"error": f"Unexpected error: {str(e)}"}
    
    def process_travel_query(self, user_query: Dict[str, Any], 
                            flight_data: Any,
                            hotel_data: Optional[Dict[str, Any]] = None,
                            restaurant_data: Optional[Dict[str, Any]] = None,
                            attraction_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a travel query using GPT-4o
        
        Args:
            user_query: User's travel query details
            flight_data: Flight information from flight API
            hotel_data: Hotel information (optional)
            restaurant_data: Restaurant information (optional)
            attraction_data: Attraction information (optional)
            
        Returns:
            Dictionary containing travel recommendations
        """
        try:
            # 构建提示词
            prompt = self._construct_travel_prompt(
                user_query, 
                flight_data, 
                hotel_data, 
                restaurant_data, 
                attraction_data
            )
            
            logger.info("Prompt constructed successfully")
            # 正确处理列表或字典类型的flight_data
            if isinstance(flight_data, dict) and 'data' in flight_data:
                logger.info(f"Flight data has {len(flight_data.get('data', []))} flights")
            elif isinstance(flight_data, list):
                logger.info(f"Flight data has {len(flight_data)} flights")
            
            # 生成推荐
            logger.info("Sending request to generate recommendations")
            response = self.generate_text(prompt, max_tokens=4000, temperature=0.5)
            
            # 检查API响应中的错误
            if "error" in response:
                logger.error(f"Error in API response: {response['error']}")
                return {"recommendations": f"Error from OpenAI API: {response['error']}"}
            
            # 提取并解析响应
            logger.info("Extracting content from response")
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            if not content:
                logger.error("Empty content received from API")
                return {"recommendations": "Error: Empty response from OpenAI API"}
            
            logger.info(f"Successfully extracted content (length: {len(content)})")
            
            # 返回原始内容
            return {"recommendations": content}
        except Exception as e:
            logger.error(f"Error in process_travel_query: {str(e)}")
            return {"recommendations": f"Failed to process travel query: {str(e)}"}
    
    def _construct_travel_prompt(self, 
                               user_query: Dict[str, Any],
                               flight_data: Any,
                               hotel_data: Optional[Dict[str, Any]] = None,
                               restaurant_data: Optional[Dict[str, Any]] = None,
                               attraction_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a prompt focused on flight options analysis
        
        Args:
            user_query: User query details
            flight_data: Flight information
            hotel_data: Hotel information (optional)
            restaurant_data: Restaurant information (optional)
            attraction_data: Attraction information (optional)
            
        Returns:
            Formatted prompt string
        """
        # Basic user query information
        prompt = f"""You are a flight analysis expert. Please analyze the following flight options and present them in a table format:

User Query:
- Origin: {user_query.get('origin', 'Not specified')}
- Destination: {user_query.get('destination', 'Not specified')}
- Departure Date: {user_query.get('departure_date', 'Not specified')}
- Return Date: {user_query.get('return_date', 'Not specified')}

Flight Information:
"""

        # Format flight data for better readability - handle both list and dict types
        flights_to_include = []
        if isinstance(flight_data, dict) and 'data' in flight_data and len(flight_data['data']) > 0:
            # If flight_data is a dictionary with 'data' key
            flights_to_include = flight_data['data'][:5]  # Only include first 5 flights
        elif isinstance(flight_data, list) and len(flight_data) > 0:
            # If flight_data is a list
            flights_to_include = flight_data[:5]  # Only include first 5 flights
        
        if flights_to_include:
            prompt += f"I found {len(flights_to_include)} flights that match your criteria. Here are the details:\n\n"
            
            # Format each flight
            for i, flight in enumerate(flights_to_include, 1):
                prompt += f"FLIGHT OPTION {i}:\n"
                
                # Price info
                price = flight.get('price', {})
                prompt += f"Price: {price.get('total', 'N/A')} {price.get('currency', '')}\n"
                
                # Itineraries
                itineraries = flight.get('itineraries', [])
                for j, itinerary in enumerate(itineraries):
                    journey_type = "OUTBOUND" if j == 0 else "RETURN"
                    prompt += f"{journey_type} JOURNEY:\n"
                    prompt += f"Duration: {itinerary.get('duration', 'N/A')}\n"
                    
                    # Segments
                    segments = itinerary.get('segments', [])
                    prompt += f"Stops: {len(segments) - 1}\n"
                    
                    for k, segment in enumerate(segments):
                        carrier = segment.get('carrierCode', 'N/A')
                        flight_number = segment.get('number', 'N/A')
                        
                        departure = segment.get('departure', {})
                        dep_time = departure.get('at', 'N/A')
                        dep_airport = departure.get('iataCode', 'N/A')
                        
                        arrival = segment.get('arrival', {})
                        arr_time = arrival.get('at', 'N/A')
                        arr_airport = arrival.get('iataCode', 'N/A')
                        
                        prompt += f"Segment {k+1}: {carrier} {flight_number}, {dep_airport}→{arr_airport}, Departure: {dep_time}, Arrival: {arr_time}\n"
                    
                    prompt += "\n"
                
                # Traveler pricing details
                traveler_pricings = flight.get('travelerPricings', [])
                if traveler_pricings:
                    traveler = traveler_pricings[0]
                    fare_details = traveler.get('fareDetailsBySegment', [])
                    if fare_details:
                        cabin_class = fare_details[0].get('cabin', 'N/A')
                        included_baggage = fare_details[0].get('includedCheckedBags', {})
                        baggage_quantity = included_baggage.get('quantity', 0) if included_baggage else 0
                        
                        prompt += f"Cabin Class: {cabin_class}\n"
                        if baggage_quantity:
                            prompt += f"Baggage Allowance: {baggage_quantity} piece(s)\n"
                        else:
                            prompt += "Baggage Allowance: Not specified\n"
                
                prompt += "\n---\n\n"
        else:
            prompt += "No flight data available.\n"

        # Add instructions for the response format
        prompt += """
Please analyze the above flight data and provide the following:

## Flight Options Analysis

Create a markdown table comparing the flight options with these columns:
- Option
- Airline
- Duration (Outbound/Return)
- Total Price
- Baggage Allowance
- Stops
- Fare Type
- Advantage

Example table format:
| Option | Airline | Duration (Outbound/Return) | Total Price | Baggage Allowance | Stops | Fare Type | Advantage |
|--------|---------|----------------------------|-------------|-------------------|-------|-----------|-----------|
| 1 | Airline Name | XXh / XXh | Price | Baggage | Stops | Fare Type | Key advantage |

For each flight option, provide a concise advantage or key characteristic in the Advantage column.

After the table, please provide a brief analysis of each option, highlighting which might be best for different traveler needs (best value, fastest, most convenient, etc.)

IMPORTANT INSTRUCTIONS:
1. DO NOT format your response as JSON
2. DO NOT include hotel, restaurant, or attraction recommendations
3. DO NOT create a travel itinerary
4. ONLY analyze the flight options based on the actual data provided
5. Use markdown tables and text only
"""
        return prompt

    def analyze_user_preferences(self, conversation_history: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        Analyze user preferences from conversation history
        
        Args:
            conversation_history: List of conversation messages
            
        Returns:
            Dictionary of extracted user preferences
        """
        # Construct the prompt for preference analysis
        messages_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation_history])
        
        prompt = f"""Analyze the following conversation between a user and a travel planning system to extract detailed user preferences:

CONVERSATION:
{messages_text}

Extract the following information:
1. Preferred destinations
2. Budget constraints
3. Travel style (luxury, budget, adventure, relaxation, etc.)
4. Accommodation preferences
5. Activity interests
6. Dining preferences
7. Any specific requirements or constraints

Format your response as a JSON object with these categories.
"""
        
        # Generate analysis
        response = self.generate_text(prompt, max_tokens=1000, temperature=0.3)
        
        # Extract and parse the response
        try:
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            # Try to parse as JSON
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"preferences_text": content}
        except Exception as e:
            return {"error": f"Failed to analyze preferences: {str(e)}"}


class AnthropicAPI:
    """API client for interacting with Anthropic Claude models"""
    
    def __init__(self, api_key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        """
        Initialize the Anthropic API client
        
        Args:
            api_key: API key for Anthropic (defaults to environment variable)
            model: Model name to use (default: claude-3-opus-20240229)
        """
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided or set as ANTHROPIC_API_KEY environment variable")
        
        self.model = model
        self.base_url = "https://api.anthropic.com/v1/messages"
        self.headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
    
    def generate_text(self, prompt: str, max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Any]:
        """
        Generate text using Claude
        
        Args:
            prompt: The prompt to send to the model
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0-1.0)
            
        Returns:
            Dictionary containing the model's response
        """
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        try:
            response = requests.post(self.base_url, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}
    
    def process_travel_query(self, user_query: Dict[str, Any], 
                            flight_data: Dict[str, Any],
                            hotel_data: Optional[Dict[str, Any]] = None,
                            restaurant_data: Optional[Dict[str, Any]] = None,
                            attraction_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a travel query using Claude
        
        Args:
            user_query: User's travel query details
            flight_data: Flight information from flight API
            hotel_data: Hotel information (optional)
            restaurant_data: Restaurant information (optional)
            attraction_data: Attraction information (optional)
            
        Returns:
            Dictionary containing travel recommendations
        """
        # Construct the prompt with all available data
        prompt = self._construct_travel_prompt(
            user_query, 
            flight_data, 
            hotel_data, 
            restaurant_data, 
            attraction_data
        )
        
        # Generate recommendations
        response = self.generate_text(prompt, max_tokens=4000, temperature=0.5)
        
        # Extract and parse the response
        try:
            content = response.get("content", [{}])[0].get("text", "")
            # Try to parse as JSON if possible
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                # If not valid JSON, return as text
                return {"recommendations": content}
        except Exception as e:
            return {"error": f"Failed to process Claude response: {str(e)}"}
    
    def _construct_travel_prompt(self, 
                               user_query: Dict[str, Any],
                               flight_data: Dict[str, Any],
                               hotel_data: Optional[Dict[str, Any]] = None,
                               restaurant_data: Optional[Dict[str, Any]] = None,
                               attraction_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Construct a prompt for travel recommendations
        
        Args:
            user_query: User's travel query details
            flight_data: Flight information
            hotel_data: Hotel information (optional)
            restaurant_data: Restaurant information (optional)
            attraction_data: Attraction information (optional)
            
        Returns:
            Formatted prompt string
        """
        # Basic user query information
        prompt = f"""You are an expert travel planner. Create a detailed travel plan based on the following information:

USER QUERY:
- Origin: {user_query.get('origin', 'Not specified')}
- Destination: {user_query.get('destination', 'Not specified')}
- Departure Date: {user_query.get('departure_date', 'Not specified')}
- Return Date: {user_query.get('return_date', 'Not specified')}
- Budget: {user_query.get('budget', 'Not specified')}
- Interests: {', '.join(user_query.get('interests', ['Not specified']))}

FLIGHT INFORMATION:
{json.dumps(flight_data, indent=2)}
"""

        # Add hotel information if available
        if hotel_data:
            prompt += f"""
HOTEL OPTIONS:
{json.dumps(hotel_data, indent=2)}
"""

        # Add restaurant information if available
        if restaurant_data:
            prompt += f"""
RESTAURANT OPTIONS:
{json.dumps(restaurant_data, indent=2)}
"""

        # Add attraction information if available
        if attraction_data:
            prompt += f"""
ATTRACTION OPTIONS:
{json.dumps(attraction_data, indent=2)}
"""

        # Add instructions for the response format
        prompt += """
Based on the above information, please provide:
1. A summary of the best flight options
2. Recommended accommodations
3. Suggested activities and attractions based on the user's interests
4. Dining recommendations
5. A day-by-day itinerary

Format your response as a JSON object with the following structure:
{
  "flight_recommendations": [...],
  "hotel_recommendations": [...],
  "activity_recommendations": [...],
  "dining_recommendations": [...],
  "itinerary": [...]
}
"""
        return prompt 