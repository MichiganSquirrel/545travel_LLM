import requests
import json
import os
from datetime import datetime

class FlightAPI:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.environ.get("FLIGHT_API_KEY")
        self.base_url = "https://api.example.com/flights"  # 实际使用时替换为真实API地址
    
    def search_flights(self, origin, destination, departure_date, return_date=None, adults=1, children=0, cabin_class="ECONOMY"):
        """
        搜索航班
        
        Args:
            origin: 出发地（城市名或机场代码）
            destination: 目的地（城市名或机场代码）
            departure_date: 出发日期（YYYY-MM-DD格式）
            return_date: 返回日期（YYYY-MM-DD格式，可选）
            adults: 成人乘客数量
            children: 儿童乘客数量
            cabin_class: 舱位等级（ECONOMY, PREMIUM_ECONOMY, BUSINESS, FIRST）
            
        Returns:
            包含航班列表的字典
        """
        params = {
            "api_key": self.api_key,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "adults": adults,
            "children": children,
            "cabin_class": cabin_class
        }
        
        if return_date:
            params["return_date"] = return_date
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_flight_details(self, flight_id):
        """获取航班详细信息"""
        try:
            response = requests.get(f"{self.base_url}/flights/{flight_id}", params={"api_key": self.api_key})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_price_history(self, origin, destination, departure_date, days=30):
        """
        获取特定航线的价格历史
        
        Args:
            origin: 出发地
            destination: 目的地
            departure_date: 出发日期
            days: 历史天数（默认30天）
            
        Returns:
            包含价格历史的字典
        """
        params = {
            "api_key": self.api_key,
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "days": days
        }
        
        try:
            response = requests.get(f"{self.base_url}/price-history", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_airport_information(self, airport_code):
        """
        获取机场信息
        
        Args:
            airport_code: 机场IATA代码
            
        Returns:
            包含机场信息的字典
        """
        try:
            response = requests.get(f"{self.base_url}/airports/{airport_code}", params={"api_key": self.api_key})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_live_flight_status(self, flight_number, date):
        """
        获取实时航班状态
        
        Args:
            flight_number: 航班号（如"CZ3456"）
            date: 航班日期（YYYY-MM-DD格式）
            
        Returns:
            包含航班状态的字典
        """
        params = {
            "api_key": self.api_key,
            "flight_number": flight_number,
            "date": date
        }
        
        try:
            response = requests.get(f"{self.base_url}/status", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def load_mock_data(self, file_path):
        """加载模拟航班数据（用于测试）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load mock data: {str(e)}"} 