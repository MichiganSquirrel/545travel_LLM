import os
import pandas as pd
import json
import datetime
import csv
from typing import Dict, List, Any, Optional

class DatabaseManager:
    """数据库管理器，用于处理用户会话数据和旅行计划"""
    
    def __init__(self, database_dir: Optional[str] = None):
        """
        初始化数据库管理器
        
        参数:
            database_dir: 数据库目录路径（可选）
        """
        if database_dir:
            self.database_dir = database_dir
        else:
            # 默认使用项目根目录下的database文件夹
            self.database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        
        # 确保数据库目录存在
        os.makedirs(self.database_dir, exist_ok=True)
        
        # 用户数据目录
        self.users_dir = os.path.join(self.database_dir, "users")
        os.makedirs(self.users_dir, exist_ok=True)
    
    def get_user_directory(self, user_id: str) -> str:
        """
        获取用户目录，如果不存在则创建
        
        参数:
            user_id: 用户ID
            
        返回:
            用户目录路径
        """
        user_dir = os.path.join(self.users_dir, user_id)
        os.makedirs(user_dir, exist_ok=True)
        
        # 确保三个必要的文件存在
        for file_name in ["temp.csv", "memory_bank.csv", "recommendations.csv"]:
            file_path = os.path.join(user_dir, file_name)
            if not os.path.exists(file_path):
                # 创建文件并写入表头
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    if file_name == "temp.csv":
                        writer.writerow(["timestamp", "data_type", "data_json"])
                    elif file_name == "memory_bank.csv":
                        writer.writerow(["timestamp", "preference_type", "preference_value", "confidence_score"])
                    elif file_name == "recommendations.csv":
                        writer.writerow(["timestamp", "destination", "start_date", "end_date", "plan_json"])
        
        return user_dir
    
    def save_temp_data(self, user_id: str, data_type: str, data: Dict[str, Any]) -> str:
        """
        保存临时数据到用户的temp.csv文件
        
        参数:
            user_id: 用户ID
            data_type: 数据类型（例如：flight, hotel, attraction等）
            data: 要保存的数据
            
        返回:
            保存的文件路径
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "temp.csv")
        
        # 准备数据
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 将数据转换为JSON字符串
        data_json = json.dumps(data, ensure_ascii=False)
        
        # 写入CSV文件
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, data_type, data_json])
        
        return file_path
    
    def get_temp_data(self, user_id: str, data_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取用户的临时数据
        
        参数:
            user_id: 用户ID
            data_type: 数据类型过滤（可选）
            
        返回:
            临时数据列表
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "temp.csv")
        
        result = []
        try:
            df = pd.read_csv(file_path)
            # 应用数据类型过滤（如果提供）
            if data_type:
                df = df[df['data_type'] == data_type]
            
            # 转换每一行到字典
            for _, row in df.iterrows():
                item = {
                    "timestamp": row["timestamp"],
                    "data_type": row["data_type"],
                    "data": json.loads(row["data_json"])
                }
                result.append(item)
                
        except Exception as e:
            print(f"读取临时数据时出错: {str(e)}")
        
        return result
    
    def clear_temp_data(self, user_id: str) -> bool:
        """
        清除用户的临时数据
        
        参数:
            user_id: 用户ID
            
        返回:
            是否成功清除
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "temp.csv")
        
        try:
            # 重新创建文件并只写入表头
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "data_type", "data_json"])
            return True
        except Exception as e:
            print(f"清除临时数据时出错: {str(e)}")
            return False
    
    def save_user_preference(self, user_id: str, preference_type: str, 
                             preference_value: str, confidence_score: float = 1.0) -> str:
        """
        保存用户偏好到记忆库
        
        参数:
            user_id: 用户ID
            preference_type: 偏好类型（例如：cuisine, airline, hotel_star等）
            preference_value: 偏好值
            confidence_score: 置信度分数（0.0-1.0）
            
        返回:
            保存的文件路径
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "memory_bank.csv")
        
        # 准备数据
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 写入CSV文件
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, preference_type, preference_value, confidence_score])
        
        return file_path
    
    def get_user_preferences(self, user_id: str, preference_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取用户偏好
        
        参数:
            user_id: 用户ID
            preference_type: 偏好类型过滤（可选）
            
        返回:
            用户偏好列表
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "memory_bank.csv")
        
        result = []
        try:
            df = pd.read_csv(file_path)
            # 应用偏好类型过滤（如果提供）
            if preference_type:
                df = df[df['preference_type'] == preference_type]
            
            # 转换每一行到字典
            for _, row in df.iterrows():
                item = {
                    "timestamp": row["timestamp"],
                    "preference_type": row["preference_type"],
                    "preference_value": row["preference_value"],
                    "confidence_score": float(row["confidence_score"])
                }
                result.append(item)
                
        except Exception as e:
            print(f"读取用户偏好时出错: {str(e)}")
        
        return result
    
    def save_recommendation(self, user_id: str, destination: str, 
                            start_date: str, end_date: str, plan: Dict[str, Any]) -> str:
        """
        保存用户的旅行推荐
        
        参数:
            user_id: 用户ID
            destination: 目的地
            start_date: 开始日期
            end_date: 结束日期
            plan: 旅行计划详情
            
        返回:
            保存的文件路径
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "recommendations.csv")
        
        # 准备数据
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 将数据转换为JSON字符串
        plan_json = json.dumps(plan, ensure_ascii=False)
        
        # 写入CSV文件
        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([timestamp, destination, start_date, end_date, plan_json])
        
        return file_path
    
    def get_user_recommendations(self, user_id: str) -> List[Dict[str, Any]]:
        """
        获取用户的旅行推荐历史
        
        参数:
            user_id: 用户ID
            
        返回:
            用户旅行推荐历史列表
        """
        user_dir = self.get_user_directory(user_id)
        file_path = os.path.join(user_dir, "recommendations.csv")
        
        result = []
        try:
            df = pd.read_csv(file_path)
            
            # 转换每一行到字典
            for _, row in df.iterrows():
                item = {
                    "timestamp": row["timestamp"],
                    "destination": row["destination"],
                    "start_date": row["start_date"],
                    "end_date": row["end_date"],
                    "plan": json.loads(row["plan_json"])
                }
                result.append(item)
                
        except Exception as e:
            print(f"读取用户推荐时出错: {str(e)}")
        
        return result
    
    def get_all_recommendations(self) -> List[Dict[str, Any]]:
        """
        获取所有用户的旅行推荐，用于聚类分析
        
        返回:
            所有用户的旅行推荐列表
        """
        all_recommendations = []
        
        # 遍历所有用户目录
        for user_id in os.listdir(self.users_dir):
            user_dir = os.path.join(self.users_dir, user_id)
            if os.path.isdir(user_dir):
                # 获取该用户的推荐
                user_recommendations = self.get_user_recommendations(user_id)
                
                # 添加用户ID
                for rec in user_recommendations:
                    rec["user_id"] = user_id
                    all_recommendations.append(rec)
        
        return all_recommendations

    def save_session(self, user_query: Dict[str, Any], 
                    selected_flight: Optional[Dict[str, Any]], 
                    all_flights: List[Dict[str, Any]], 
                    user_feedback: str) -> str:
        """
        Save user session data to CSV file
        
        Args:
            user_query: User query information
            selected_flight: User selected flight (optional)
            all_flights: All flight options
            user_feedback: User feedback
            
        Returns:
            Path to the saved file
        """
        # Create unique filename
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        user_id = user_query.get("user_id", "unknown")
        filename = os.path.join(self.database_dir, f"session_{user_id}_{timestamp}.csv")
        
        # Prepare session data
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
        
        # Write data to CSV file
        df = pd.DataFrame([session_data])
        df.to_csv(filename, index=False)
        
        return filename
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user flight search history
        
        Args:
            user_id: User ID
            
        Returns:
            List of user's previous sessions
        """
        history = []
        
        # Find all files for this user
        for filename in os.listdir(self.database_dir):
            if filename.startswith(f"session_{user_id}_") and filename.endswith(".csv"):
                file_path = os.path.join(self.database_dir, filename)
                try:
                    # Read the CSV file
                    df = pd.read_csv(file_path)
                    if not df.empty:
                        # Convert to dictionary
                        session = df.iloc[0].to_dict()
                        
                        # Parse JSON fields
                        if "selected_flight" in session and session["selected_flight"] != "None":
                            try:
                                session["selected_flight"] = json.loads(session["selected_flight"])
                            except:
                                session["selected_flight"] = None
                        
                        history.append(session)
                except Exception as e:
                    print(f"Error reading file {file_path}: {str(e)}")
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        return history
    
    def get_user_preferences(self, user_id: str) -> Dict[str, Any]:
        """
        Extract user preferences from history
        
        Args:
            user_id: User ID
            
        Returns:
            Dictionary of user preferences
        """
        history = self.get_user_history(user_id)
        preferences = {
            "frequent_destinations": {},
            "preferred_airlines": {},
            "cabin_class": {},
            "typical_trip_duration": []
        }
        
        for session in history:
            # Count destinations
            destination = session.get("destination")
            if destination:
                if destination in preferences["frequent_destinations"]:
                    preferences["frequent_destinations"][destination] += 1
                else:
                    preferences["frequent_destinations"][destination] = 1
            
            # Extract selected flight info
            selected_flight = session.get("selected_flight")
            if selected_flight and isinstance(selected_flight, dict):
                # Count airlines
                for itinerary in selected_flight.get("itineraries", []):
                    for segment in itinerary.get("segments", []):
                        airline = segment.get("carrierCode")
                        if airline:
                            if airline in preferences["preferred_airlines"]:
                                preferences["preferred_airlines"][airline] += 1
                            else:
                                preferences["preferred_airlines"][airline] = 1
                
                # Count cabin class
                cabin = selected_flight.get("travelerPricings", [{}])[0].get("fareDetailsBySegment", [{}])[0].get("cabin")
                if cabin:
                    if cabin in preferences["cabin_class"]:
                        preferences["cabin_class"][cabin] += 1
                    else:
                        preferences["cabin_class"][cabin] = 1
            
            # Calculate trip duration
            departure_date = session.get("departure_date")
            return_date = session.get("return_date")
            if departure_date and return_date:
                try:
                    d1 = datetime.datetime.strptime(departure_date, "%Y-%m-%d")
                    d2 = datetime.datetime.strptime(return_date, "%Y-%m-%d")
                    duration = (d2 - d1).days
                    preferences["typical_trip_duration"].append(duration)
                except:
                    pass
        
        # Calculate average trip duration
        if preferences["typical_trip_duration"]:
            preferences["average_trip_duration"] = sum(preferences["typical_trip_duration"]) / len(preferences["typical_trip_duration"])
        else:
            preferences["average_trip_duration"] = None
        
        return preferences 