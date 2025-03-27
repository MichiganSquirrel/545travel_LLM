import requests
import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional

class HotelAPI:
    def __init__(self, api_key=None, google_maps_api_key=None):
        # 初始化API密钥
        self.api_key = api_key or os.environ.get("HOTEL_API_KEY")
        self.google_maps_api_key = google_maps_api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        
        # 检查Google Maps API密钥
        if not self.google_maps_api_key:
            print("警告: 没有提供Google Maps API密钥，某些功能可能无法使用")
            
        # API端点
        self.base_url = "https://hotel-api.example.com/v1"  # 实际使用时替换为真实API地址
        self.google_maps_base_url = "https://maps.googleapis.com/maps/api"
    
    def search_hotels(self, location, check_in, check_out, guests=1, rooms=1, star_rating=None, price_range=None, radius=5000, language="zh-CN"):
        """
        搜索酒店，优先使用Google Maps API
        
        Args:
            location: 位置（城市名或经纬度，如"上海"或"31.2304,121.4737"）
            check_in: 入住日期（YYYY-MM-DD格式）
            check_out: 退房日期（YYYY-MM-DD格式）
            guests: 客人数量
            rooms: 房间数量
            star_rating: 最低星级（1-5）
            price_range: 价格范围字典，含有min和max字段
            radius: 搜索半径（米），仅当使用Google Maps API时适用
            language: 返回结果的语言
            
        Returns:
            包含酒店列表的字典
        """
        # 尝试使用Google Maps API
        if self.google_maps_api_key:
            return self._search_hotels_google_maps(location, check_in, check_out, guests, rooms, star_rating, price_range, radius, language)
        
        # 降级到备用API
        params = {
            "api_key": self.api_key,
            "location": location,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms
        }
        
        # 添加可选参数
        if star_rating:
            params["star_rating"] = star_rating
        
        if price_range:
            params["price_min"] = price_range.get("min")
            params["price_max"] = price_range.get("max")
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def _search_hotels_google_maps(self, location, check_in, check_out, guests=1, rooms=1, star_rating=None, price_range=None, radius=5000, language="zh-CN"):
        """使用Google Maps Places API搜索酒店"""
        # 检查位置格式
        if "," in location and len(location.split(",")) == 2:
            # 已经是经纬度格式
            lat_lng = location
        else:
            # 城市名，需要先进行地理编码
            lat_lng = self._geocode_location(location, language)
            if "error" in lat_lng:
                return lat_lng  # 返回地理编码错误
        
        # 构建查询关键词，可以添加星级或价格相关词汇
        query = "酒店"
        if star_rating:
            query = f"{star_rating}星级 {query}"
            
        # 价格级别映射
        price_level = None
        if price_range:
            # 根据价格范围粗略确定价格级别（1-4，对应$-$$$$）
            min_price = price_range.get("min", 0)
            if min_price > 1000:
                price_level = 4  # 高档
            elif min_price > 500:
                price_level = 3  # 中高档
            elif min_price > 300:
                price_level = 2  # 中档
            else:
                price_level = 1  # 经济型
        
        # 构建请求参数
        url = f"{self.google_maps_base_url}/place/textsearch/json"
        params = {
            "query": query,
            "location": lat_lng,
            "radius": radius,
            "type": "lodging",  # 酒店类型
            "language": language,
            "key": self.google_maps_api_key
        }
        
        if price_level:
            params["minprice"] = price_level - 1  # 调整为Google Maps API的0-3范围
            params["maxprice"] = price_level
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            places_data = response.json()
            
            # 转换Google Places API的结果格式为我们的标准格式
            return self._format_google_places_results(places_data, check_in, check_out, guests, rooms)
        except Exception as e:
            return {"error": f"Google Maps API 搜索失败: {str(e)}"}
    
    def _geocode_location(self, location_name, language="zh-CN"):
        """将地点名称转换为经纬度"""
        url = f"{self.google_maps_base_url}/geocode/json"
        params = {
            "address": location_name,
            "language": language,
            "key": self.google_maps_api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            geocode_data = response.json()
            
            if geocode_data["status"] == "OK" and geocode_data["results"]:
                location = geocode_data["results"][0]["geometry"]["location"]
                return f"{location['lat']},{location['lng']}"
            else:
                return {"error": f"地理编码失败: {geocode_data['status']}"}
        except Exception as e:
            return {"error": f"地理编码请求失败: {str(e)}"}
    
    def _format_google_places_results(self, places_data, check_in, check_out, guests, rooms):
        """将Google Places API结果转换为标准格式"""
        if places_data["status"] != "OK":
            return {"error": f"Google Places API返回错误: {places_data['status']}"}
        
        hotels = []
        for place in places_data.get("results", []):
            # 基本信息
            hotel = {
                "id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng")
                },
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "price_level": place.get("price_level")
            }
            
            # 添加照片信息（如果有）
            if "photos" in place and place["photos"]:
                hotel["photos"] = [{
                    "reference": photo.get("photo_reference"),
                    "width": photo.get("width"),
                    "height": photo.get("height")
                } for photo in place["photos"]]
            
            # 添加入住信息
            hotel["check_in"] = check_in
            hotel["check_out"] = check_out
            hotel["guests"] = guests
            hotel["rooms"] = rooms
            
            hotels.append(hotel)
        
        return {
            "hotels": hotels,
            "count": len(hotels),
            "status": "success",
            "source": "google_maps"
        }
    
    def get_hotel_details(self, hotel_id, language="zh-CN"):
        """
        获取酒店详细信息
        
        Args:
            hotel_id: 酒店ID（如Google Places API的place_id）
            language: 返回结果的语言
            
        Returns:
            包含酒店详细信息的字典
        """
        # 优先使用Google Maps Places API
        if self.google_maps_api_key:
            return self._get_hotel_details_google_maps(hotel_id, language)
        
        # 备用API
        try:
            response = requests.get(f"{self.base_url}/hotels/{hotel_id}", params={"api_key": self.api_key})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def _get_hotel_details_google_maps(self, place_id, language="zh-CN"):
        """使用Google Maps Places API获取酒店详情"""
        url = f"{self.google_maps_base_url}/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_address,formatted_phone_number,website,opening_hours,price_level,review,photo,geometry,address_component,international_phone_number",
            "language": language,
            "key": self.google_maps_api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            details_data = response.json()
            
            if details_data["status"] != "OK":
                return {"error": f"获取酒店详情失败: {details_data['status']}"}
            
            # 转换为标准格式
            result = details_data["result"]
            hotel_details = {
                "id": place_id,
                "name": result.get("name"),
                "address": result.get("formatted_address"),
                "phone": result.get("formatted_phone_number"),
                "website": result.get("website"),
                "location": {
                    "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": result.get("geometry", {}).get("location", {}).get("lng")
                },
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total"),
                "price_level": result.get("price_level")
            }
            
            # 添加照片信息
            if "photos" in result:
                hotel_details["photos"] = [{
                    "reference": photo.get("photo_reference"),
                    "width": photo.get("width"),
                    "height": photo.get("height")
                } for photo in result["photos"]]
            
            # 添加评论信息
            if "reviews" in result:
                hotel_details["reviews"] = [{
                    "author": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": review.get("text"),
                    "time": review.get("time"),
                    "relative_time": review.get("relative_time_description")
                } for review in result["reviews"]]
            
            return {"hotel": hotel_details, "status": "success", "source": "google_maps"}
        except Exception as e:
            return {"error": f"获取酒店详情请求失败: {str(e)}"}
    
    def get_hotel_photos(self, photo_reference, max_width=800, max_height=None):
        """
        获取酒店照片
        
        Args:
            photo_reference: 照片引用ID（来自Google Places API）
            max_width: 最大宽度
            max_height: 最大高度（可选）
            
        Returns:
            包含照片URL的字典
        """
        if not self.google_maps_api_key:
            return {"error": "没有提供Google Maps API密钥"}
            
        url = f"{self.google_maps_base_url}/place/photo"
        params = {
            "photoreference": photo_reference,
            "key": self.google_maps_api_key
        }
        
        if max_width:
            params["maxwidth"] = max_width
        if max_height:
            params["maxheight"] = max_height
            
        try:
            # Google Photo API返回的是重定向，而不是JSON
            response = requests.get(url, params=params, allow_redirects=False)
            
            if response.status_code == 302:  # 重定向状态码
                photo_url = response.headers.get("Location")
                return {"photo_url": photo_url, "status": "success"}
            else:
                return {"error": f"获取照片失败: {response.status_code}", "content": response.text}
        except Exception as e:
            return {"error": f"获取照片请求失败: {str(e)}"}
    
    def get_room_availability(self, hotel_id, check_in, check_out, guests=1, rooms=1):
        """获取酒店房间可用性"""
        # Google Maps API不提供直接的房间可用性信息
        # 这里使用备用API
        params = {
            "api_key": self.api_key,
            "check_in": check_in,
            "check_out": check_out,
            "guests": guests,
            "rooms": rooms
        }
        
        try:
            response = requests.get(f"{self.base_url}/hotels/{hotel_id}/rooms", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e), "message": "Google Maps API不提供房间可用性信息，需要集成专门的酒店预订API"}
    
    def load_mock_data(self, file_path):
        """加载模拟酒店数据（用于测试）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load mock data: {str(e)}"}