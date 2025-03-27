import requests
import json
import os
from typing import Dict, List, Any, Optional

class AttractionAPI:
    def __init__(self, api_key=None, google_maps_api_key=None):
        # 初始化API密钥
        self.api_key = api_key or os.environ.get("ATTRACTION_API_KEY")
        self.google_maps_api_key = google_maps_api_key or os.environ.get("GOOGLE_MAPS_API_KEY")
        
        # 检查Google Maps API密钥
        if not self.google_maps_api_key:
            print("警告: 没有提供Google Maps API密钥，某些功能可能无法使用")
            
        # API端点
        self.base_url = "https://attraction-api.example.com/v1"  # 实际使用时替换为真实API地址
        self.google_maps_base_url = "https://maps.googleapis.com/maps/api"
    
    def search_attractions(self, location, category=None, rating=None, price_range=None, limit=20, language="zh-CN"):
        """
        搜索景点，优先使用Google Maps API
        
        Args:
            location: 位置（城市名或经纬度，如"上海"或"31.2304,121.4737"）
            category: 景点类别，如"museum"、"park"等（可选）
            rating: 最低评分，1-5（可选）
            price_range: 价格范围字典，包含min和max（可选）
            limit: 返回结果数量
            language: 返回结果的语言
            
        Returns:
            包含景点列表的字典
        """
        # 尝试使用Google Maps API
        if self.google_maps_api_key:
            return self._search_attractions_google_maps(location, category, rating, price_range, limit, language)
        
        # 降级到备用API
        params = {
            "api_key": self.api_key,
            "location": location,
            "limit": limit
        }
        
        # 添加可选参数
        if category:
            params["category"] = category
        
        if rating:
            params["rating"] = rating
        
        if price_range:
            params["price_min"] = price_range.get("min")
            params["price_max"] = price_range.get("max")
        
        try:
            response = requests.get(f"{self.base_url}/search", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def _search_attractions_google_maps(self, location, category=None, rating=None, price_range=None, limit=20, language="zh-CN"):
        """使用Google Maps Places API搜索景点"""
        # 检查位置格式
        if "," in location and len(location.split(",")) == 2:
            # 已经是经纬度格式
            lat_lng = location
        else:
            # 城市名，需要先进行地理编码
            lat_lng = self._geocode_location(location, language)
            if isinstance(lat_lng, dict) and "error" in lat_lng:
                return lat_lng  # 返回地理编码错误
        
        # 映射景点类别到Google Place类型
        place_type = "tourist_attraction"  # 默认为旅游景点
        if category:
            # 映射类别
            category_map = {
                "museum": "museum",
                "park": "park",
                "zoo": "zoo",
                "amusement_park": "amusement_park",
                "aquarium": "aquarium",
                "art_gallery": "art_gallery",
                "natural_feature": "natural_feature",
                "historic_site": "point_of_interest",
                "shopping": "shopping_mall",
                "entertainment": "movie_theater"
            }
            place_type = category_map.get(category, "tourist_attraction")
        
        # 构建查询关键词，会更好地结合地点和类型
        query = "景点"
        if category:
            if category == "museum":
                query = "博物馆"
            elif category == "park":
                query = "公园"
            elif category == "zoo":
                query = "动物园"
            elif category == "amusement_park":
                query = "游乐园"
            elif category == "aquarium":
                query = "水族馆"
            elif category == "art_gallery":
                query = "美术馆"
            elif category == "historic_site":
                query = "历史景点"
        
        # 构建请求参数 - 使用textsearch API获取更好的结果
        url = f"{self.google_maps_base_url}/place/textsearch/json"
        params = {
            "query": query,
            "location": lat_lng,
            "radius": 50000,  # 设置较大的半径以获取足够的结果
            "language": language,
            "key": self.google_maps_api_key
        }
        
        # 添加类型过滤（如果不是通用景点，则添加具体类型）
        if place_type != "tourist_attraction":
            params["type"] = place_type
            
        # 如果是通用景点搜索，添加type以获取更好的结果
        else:
            params["type"] = "tourist_attraction"
            
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            places_data = response.json()
            
            # 如果指定了评分过滤
            if rating:
                # 过滤评分低于指定值的结果
                min_rating = float(rating)
                if places_data["status"] == "OK":
                    places_data["results"] = [
                        place for place in places_data["results"] 
                        if "rating" in place and place["rating"] >= min_rating
                    ]
            
            # 限制结果数量
            if places_data["status"] == "OK" and limit:
                places_data["results"] = places_data["results"][:limit]
            
            # 转换Google Places API的结果格式为我们的标准格式
            return self._format_google_places_results(places_data)
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
    
    def _format_google_places_results(self, places_data):
        """将Google Places API结果转换为标准格式"""
        if places_data["status"] != "OK":
            return {"error": f"Google Places API返回错误: {places_data['status']}"}
        
        attractions = []
        for place in places_data.get("results", []):
            # 基本信息
            attraction = {
                "id": place.get("place_id"),
                "name": place.get("name"),
                "address": place.get("formatted_address"),
                "location": {
                    "lat": place.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": place.get("geometry", {}).get("location", {}).get("lng")
                },
                "rating": place.get("rating"),
                "user_ratings_total": place.get("user_ratings_total"),
                "price_level": place.get("price_level"),
                "types": place.get("types", [])
            }
            
            # 添加照片信息（如果有）
            if "photos" in place and place["photos"]:
                attraction["photos"] = [{
                    "reference": photo.get("photo_reference"),
                    "width": photo.get("width"),
                    "height": photo.get("height")
                } for photo in place["photos"]]
            
            attractions.append(attraction)
        
        return {
            "attractions": attractions,
            "count": len(attractions),
            "status": "success",
            "source": "google_maps"
        }
    
    def get_attraction_details(self, attraction_id, language="zh-CN"):
        """
        获取景点详细信息
        
        Args:
            attraction_id: 景点ID（如Google Places API的place_id）
            language: 返回结果的语言
            
        Returns:
            包含景点详细信息的字典
        """
        # 优先使用Google Maps Places API
        if self.google_maps_api_key:
            return self._get_attraction_details_google_maps(attraction_id, language)
        
        # 备用API
        try:
            response = requests.get(f"{self.base_url}/attractions/{attraction_id}", params={"api_key": self.api_key})
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def _get_attraction_details_google_maps(self, place_id, language="zh-CN"):
        """使用Google Maps Places API获取景点详情"""
        url = f"{self.google_maps_base_url}/place/details/json"
        params = {
            "place_id": place_id,
            "fields": "name,rating,formatted_address,formatted_phone_number,website,opening_hours,price_level,review,photo,geometry,address_component,international_phone_number,type,editorial_summary",
            "language": language,
            "key": self.google_maps_api_key
        }
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            details_data = response.json()
            
            if details_data["status"] != "OK":
                return {"error": f"获取景点详情失败: {details_data['status']}"}
            
            # 转换为标准格式
            result = details_data["result"]
            attraction_details = {
                "id": place_id,
                "name": result.get("name"),
                "address": result.get("formatted_address"),
                "phone": result.get("formatted_phone_number"),
                "website": result.get("website"),
                "types": result.get("types", []),
                "location": {
                    "lat": result.get("geometry", {}).get("location", {}).get("lat"),
                    "lng": result.get("geometry", {}).get("location", {}).get("lng")
                },
                "rating": result.get("rating"),
                "user_ratings_total": result.get("user_ratings_total"),
                "price_level": result.get("price_level")
            }
            
            # 添加描述信息（如果有）
            if "editorial_summary" in result and "overview" in result["editorial_summary"]:
                attraction_details["description"] = result["editorial_summary"]["overview"]
            
            # 添加营业时间
            if "opening_hours" in result and "weekday_text" in result["opening_hours"]:
                attraction_details["opening_hours"] = result["opening_hours"]["weekday_text"]
            
            # 添加照片信息
            if "photos" in result:
                attraction_details["photos"] = [{
                    "reference": photo.get("photo_reference"),
                    "width": photo.get("width"),
                    "height": photo.get("height")
                } for photo in result["photos"]]
            
            # 添加评论信息
            if "reviews" in result:
                attraction_details["reviews"] = [{
                    "author": review.get("author_name"),
                    "rating": review.get("rating"),
                    "text": review.get("text"),
                    "time": review.get("time"),
                    "relative_time": review.get("relative_time_description")
                } for review in result["reviews"]]
            
            return {"attraction": attraction_details, "status": "success", "source": "google_maps"}
        except Exception as e:
            return {"error": f"获取景点详情请求失败: {str(e)}"}
    
    def get_attraction_photos(self, photo_reference, max_width=800, max_height=None):
        """
        获取景点照片
        
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
    
    def get_attraction_reviews(self, attraction_id, limit=10, offset=0):
        """获取景点评论（使用备用API或从详情中提取）"""
        # 尝试使用Google Maps API获取详情并提取评论
        if self.google_maps_api_key:
            details = self._get_attraction_details_google_maps(attraction_id)
            if "attraction" in details and "reviews" in details["attraction"]:
                # 提取并分页处理评论
                reviews = details["attraction"]["reviews"]
                total = len(reviews)
                reviews = reviews[offset:offset+limit] if offset < total else []
                
                return {
                    "reviews": reviews,
                    "total": total,
                    "offset": offset,
                    "limit": limit,
                    "status": "success",
                    "source": "google_maps"
                }
        
        # 降级到备用API
        params = {
            "api_key": self.api_key,
            "limit": limit,
            "offset": offset
        }
        
        try:
            response = requests.get(f"{self.base_url}/attractions/{attraction_id}/reviews", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def get_nearby_attractions(self, lat, lng, radius=5000, limit=10, category=None, language="zh-CN"):
        """
        获取附近的景点
        
        Args:
            lat: 纬度
            lng: 经度
            radius: 搜索半径（米）
            limit: 返回结果数量
            category: 景点类别（可选）
            language: 返回结果的语言
            
        Returns:
            包含景点列表的字典
        """
        # 优先使用Google Maps API
        if self.google_maps_api_key:
            # 构建位置字符串
            location = f"{lat},{lng}"
            
            # 映射景点类别到Google Place类型
            place_type = "tourist_attraction"  # 默认为旅游景点
            if category:
                # 映射类别
                category_map = {
                    "museum": "museum",
                    "park": "park",
                    "zoo": "zoo",
                    "amusement_park": "amusement_park",
                    "aquarium": "aquarium",
                    "art_gallery": "art_gallery"
                }
                place_type = category_map.get(category, "tourist_attraction")
            
            # 使用nearbysearch API
            url = f"{self.google_maps_base_url}/place/nearbysearch/json"
            params = {
                "location": location,
                "radius": radius,
                "type": place_type,
                "language": language,
                "key": self.google_maps_api_key
            }
            
            try:
                response = requests.get(url, params=params)
                response.raise_for_status()
                places_data = response.json()
                
                # 限制结果数量
                if places_data["status"] == "OK" and limit:
                    places_data["results"] = places_data["results"][:limit]
                    
                # 转换Google Places API的结果格式为我们的标准格式
                return self._format_google_places_results(places_data)
            except Exception as e:
                return {"error": f"搜索附近景点失败: {str(e)}"}
                
        # 降级到备用API
        params = {
            "api_key": self.api_key,
            "lat": lat,
            "lng": lng,
            "radius": radius,
            "limit": limit
        }
        
        if category:
            params["category"] = category
        
        try:
            response = requests.get(f"{self.base_url}/nearby", params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            return {"error": str(e)}
    
    def load_mock_data(self, file_path):
        """加载模拟景点数据（用于测试）"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            return {"error": f"Failed to load mock data: {str(e)}"}