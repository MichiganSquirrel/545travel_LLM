import os
import pandas as pd
import json
import datetime
import logging
from typing import Dict, List, Any, Optional

# Import LLM API
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.llm_api import LLMApi

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename='app.log'
)
logger = logging.getLogger("db_manager")

class DatabaseManager:
    """Database manager for handling user session data with simplified structure"""
    
    def __init__(self, database_dir: Optional[str] = None):
        """
        Initialize the database manager
        
        Args:
            database_dir: Database directory path (optional)
        """
        if database_dir:
            self.database_dir = database_dir
        else:
            # Default to database folder in project root
            self.database_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "database")
        
        # Ensure database directory exists
        os.makedirs(self.database_dir, exist_ok=True)
        
        # Try to initialize LLM API
        try:
            self.llm_api = LLMApi()
            logger.info("Successfully connected to LLM API for database operations")
        except Exception as e:
            logger.error(f"Failed to initialize LLM API: {str(e)}")
            self.llm_api = None
    
    def _get_user_dir(self, user_id: str) -> str:
        """
        Get or create user directory
        
        Args:
            user_id: User ID
            
        Returns:
            Path to user directory
        """
        user_dir = os.path.join(self.database_dir, f"user_{user_id}")
        os.makedirs(user_dir, exist_ok=True)
        return user_dir
    
    def save_temp_data(self, user_query: Dict[str, Any], 
                    selected_flight: Optional[Dict[str, Any]], 
                    all_flights: List[Dict[str, Any]]) -> str:
        """
        Save temporary session data to temp.csv file in user directory
        
        Args:
            user_query: User query information
            selected_flight: User selected flight (optional)
            all_flights: All flight options
            
        Returns:
            Path to the saved file
        """
        user_id = user_query.get("user_id", "unknown")
        user_dir = self._get_user_dir(user_id)
        
        # Create filepath
        filename = os.path.join(user_dir, "temp.csv")
        
        # 提取关键信息
        origin = user_query.get("origin", "")
        destination = user_query.get("destination", "")
        
        # 初始化变量
        arrival_time = ""  # 到达目的地的时间
        departure_time = ""  # 离开目的地的时间
        cabin_type = "ECONOMY"  # 默认舱位类型
        
        if selected_flight:
            logger.info("Extracting key information from selected flight for CSV")
            
            # 获取舱位类型
            if "travelerPricings" in selected_flight and len(selected_flight["travelerPricings"]) > 0:
                traveler = selected_flight["travelerPricings"][0]
                if "fareDetailsBySegment" in traveler and len(traveler["fareDetailsBySegment"]) > 0:
                    segment = traveler["fareDetailsBySegment"][0]
                    if "cabin" in segment:
                        cabin_type = segment.get("cabin", "ECONOMY")
            
            # 提取到达目的地的时间（去程最后一段的到达时间）
            if "itineraries" in selected_flight and len(selected_flight["itineraries"]) > 0:
                outbound = selected_flight["itineraries"][0]
                if "segments" in outbound and len(outbound["segments"]) > 0:
                    # 获取去程最后一段
                    last_segment = outbound["segments"][-1]
                    if "arrival" in last_segment and "at" in last_segment["arrival"]:
                        arrival_time = last_segment["arrival"].get("at", "")
            
            # 提取离开目的地的时间（返程第一段的出发时间）
            if "itineraries" in selected_flight and len(selected_flight["itineraries"]) > 1:
                return_journey = selected_flight["itineraries"][1]
                if "segments" in return_journey and len(return_journey["segments"]) > 0:
                    # 获取返程第一段
                    first_segment = return_journey["segments"][0]
                    if "departure" in first_segment and "at" in first_segment["departure"]:
                        departure_time = first_segment["departure"].get("at", "")
        
        # 准备CSV数据 - 只包含需要的字段
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        session_data = {
            "timestamp": timestamp,
            "origin": origin,
            "destination": destination,
            "arrival_time": arrival_time,
            "departure_time": departure_time,
            "cabin_type": cabin_type,
            # 初始化偏好字段为0（表示未选择）
            "activity_interests_cultural": "0", 
            "activity_interests_nature_outdoors": "0",
            "activity_interests_entertainment": "0",
            "activity_interests_shopping": "0",
            "activity_interests_recreation": "0",
            "activity_interests_nightlife": "0",
            "hotel_preferences": "",   
            "food_preferences_asian": "0",
            "food_preferences_european": "0",
            "food_preferences_american_latin": "0",
            "food_preferences_middle_eastern": "0",
            "food_preferences_african": "0",
            "food_preferences_caribbean": "0",
            "food_preferences_local_cuisine": "0"
        }
        
        # 写入CSV文件
        df = pd.DataFrame([session_data])
        df.to_csv(filename, index=False)
        
        logger.info(f"Saved minimal flight data to {filename}")
        return filename, session_data
    
    def update_temp_with_preferences(self, user_id: str, user_preferences: Dict[str, Any]) -> str:
        """
        Update temp.csv with user's additional travel preferences
        
        Args:
            user_id: User ID
            user_preferences: User's additional travel preferences (e.g., accommodation, activities)
            
        Returns:
            Path to the updated file
        """
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "temp.csv")
        
        logger.info(f"Attempting to update temp.csv with preferences for user {user_id}")
        logger.info(f"File path: {filename}")
        
        # Check if file exists
        if not os.path.exists(filename):
            logger.warning(f"Temp file {filename} does not exist for user {user_id}, creating it")
            
            # Create a new file with minimal structure
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            initial_data = {
                "timestamp": timestamp,
                "user_id": user_id,
                "origin": user_preferences.get("origin", ""),
                "destination": user_preferences.get("destination", ""),
                "arrival_time": user_preferences.get("arrival_time", ""),
                "departure_time": user_preferences.get("departure_time", ""),
                "cabin_type": user_preferences.get("cabin_type", "ECONOMY"),
                # 添加详细的偏好字段
                "activity_interests_cultural": self._extract_specific_interest(user_preferences, "Cultural"),
                "activity_interests_nature_outdoors": self._extract_specific_interest(user_preferences, "Nature & Outdoors"),
                "activity_interests_entertainment": self._extract_specific_interest(user_preferences, "Entertainment"),
                "activity_interests_shopping": self._extract_specific_interest(user_preferences, "Shopping"),
                "activity_interests_recreation": self._extract_specific_interest(user_preferences, "Recreation"),
                "activity_interests_nightlife": self._extract_specific_interest(user_preferences, "Nightlife"),
                # 食物偏好
                "food_preferences_asian": self._extract_specific_cuisine(user_preferences, "Asian"),
                "food_preferences_european": self._extract_specific_cuisine(user_preferences, "European"),
                "food_preferences_american_latin": self._extract_specific_cuisine(user_preferences, "American/Latin"),
                "food_preferences_middle_eastern": self._extract_specific_cuisine(user_preferences, "Middle Eastern"),
                "food_preferences_african": self._extract_specific_cuisine(user_preferences, "African"),
                "food_preferences_caribbean": self._extract_specific_cuisine(user_preferences, "Caribbean"),
                "food_preferences_local_cuisine": self._extract_specific_cuisine(user_preferences, "Local Cuisine"),
                # 酒店偏好
                "hotel_preferences": self._extract_hotel_preferences(user_preferences)
            }
            
            # Create the initial dataframe
            df = pd.DataFrame([initial_data])
            
            # Save to CSV
            df.to_csv(filename, index=False)
            logger.info(f"Created new temp file with preferences: {filename}")
            return filename, initial_data
            
        try:
            # Read existing data
            logger.info(f"Reading existing temp file: {filename}")
            
            try:
                existing_df = pd.read_csv(filename)
                logger.info(f"Successfully read temp file with {len(existing_df)} rows")
            except pd.errors.EmptyDataError:
                logger.warning(f"Empty CSV file: {filename}")
                # Handle empty file case - create new dataframe with all required columns
                columns = ["timestamp", "user_id", "origin", "destination", "arrival_time", "departure_time", "cabin_type",
                          "activity_interests_cultural", "activity_interests_nature_outdoors", "activity_interests_entertainment",
                          "activity_interests_shopping", "activity_interests_recreation", "activity_interests_nightlife",
                          "hotel_preferences", "food_preferences_asian", "food_preferences_european", "food_preferences_american_latin",
                          "food_preferences_middle_eastern", "food_preferences_african", "food_preferences_caribbean", 
                          "food_preferences_local_cuisine"]
                existing_df = pd.DataFrame(columns=columns)
                
                # 设置默认值
                for col in existing_df.columns:
                    if col == "hotel_preferences":
                        existing_df[col] = ""
                    elif col.startswith("activity_interests_") or col.startswith("food_preferences_"):
                        existing_df[col] = "0"
            
            if existing_df.empty:
                logger.warning(f"Empty dataframe after reading {filename}")
                # Create a new row if the dataframe is empty
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_row = {
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "origin": user_preferences.get("origin", ""),
                    "destination": user_preferences.get("destination", ""),
                    "arrival_time": user_preferences.get("arrival_time", ""),
                    "departure_time": user_preferences.get("departure_time", ""),
                    "cabin_type": user_preferences.get("cabin_type", "ECONOMY"),
                    # 添加详细的偏好字段
                    "activity_interests_cultural": self._extract_specific_interest(user_preferences, "Cultural"),
                    "activity_interests_nature_outdoors": self._extract_specific_interest(user_preferences, "Nature & Outdoors"),
                    "activity_interests_entertainment": self._extract_specific_interest(user_preferences, "Entertainment"),
                    "activity_interests_shopping": self._extract_specific_interest(user_preferences, "Shopping"),
                    "activity_interests_recreation": self._extract_specific_interest(user_preferences, "Recreation"),
                    "activity_interests_nightlife": self._extract_specific_interest(user_preferences, "Nightlife"),
                    # 食物偏好
                    "food_preferences_asian": self._extract_specific_cuisine(user_preferences, "Asian"),
                    "food_preferences_european": self._extract_specific_cuisine(user_preferences, "European"),
                    "food_preferences_american_latin": self._extract_specific_cuisine(user_preferences, "American/Latin"),
                    "food_preferences_middle_eastern": self._extract_specific_cuisine(user_preferences, "Middle Eastern"),
                    "food_preferences_african": self._extract_specific_cuisine(user_preferences, "African"),
                    "food_preferences_caribbean": self._extract_specific_cuisine(user_preferences, "Caribbean"),
                    "food_preferences_local_cuisine": self._extract_specific_cuisine(user_preferences, "Local Cuisine"),
                    # 酒店偏好
                    "hotel_preferences": self._extract_hotel_preferences(user_preferences)
                }
                existing_df = pd.DataFrame([new_row])
                logger.info(f"Created new row for empty dataframe")
            
            # 确保所有偏好列存在
            preference_columns = [
                "activity_interests_cultural", "activity_interests_nature_outdoors", "activity_interests_entertainment",
                "activity_interests_shopping", "activity_interests_recreation", "activity_interests_nightlife",
                "hotel_preferences", "food_preferences_asian", "food_preferences_european", "food_preferences_american_latin",
                "food_preferences_middle_eastern", "food_preferences_african", "food_preferences_caribbean", 
                "food_preferences_local_cuisine"
            ]
            
            # 检查是否存在新的列，如果不存在则添加
            for column_name in preference_columns:
                if column_name not in existing_df.columns:
                    logger.info(f"'{column_name}' column not found, adding it")
                    # 对偏好类型列使用"0"作为默认值，对hotel_preferences使用空字符串
                    if column_name == "hotel_preferences":
                        existing_df[column_name] = ""  # 添加默认空值
                    else:
                        existing_df[column_name] = "0"  # 添加默认为未选择
            
            # 删除user_preferences列（如果存在）
            if "user_preferences" in existing_df.columns:
                logger.info("Removing redundant user_preferences column")
                existing_df = existing_df.drop("user_preferences", axis=1)
            
            # FIXED: Only update the most recent row, not all rows
            # Get the most recent row (last row)
            if len(existing_df) > 0:
                last_row_idx = len(existing_df) - 1
                
                # 更新特定偏好列
                existing_df.at[last_row_idx, "activity_interests_cultural"] = self._extract_specific_interest(user_preferences, "Cultural")
                existing_df.at[last_row_idx, "activity_interests_nature_outdoors"] = self._extract_specific_interest(user_preferences, "Nature & Outdoors")
                existing_df.at[last_row_idx, "activity_interests_entertainment"] = self._extract_specific_interest(user_preferences, "Entertainment")
                existing_df.at[last_row_idx, "activity_interests_shopping"] = self._extract_specific_interest(user_preferences, "Shopping")
                existing_df.at[last_row_idx, "activity_interests_recreation"] = self._extract_specific_interest(user_preferences, "Recreation")
                existing_df.at[last_row_idx, "activity_interests_nightlife"] = self._extract_specific_interest(user_preferences, "Nightlife")
                
                # 更新食物偏好
                existing_df.at[last_row_idx, "food_preferences_asian"] = self._extract_specific_cuisine(user_preferences, "Asian")
                existing_df.at[last_row_idx, "food_preferences_european"] = self._extract_specific_cuisine(user_preferences, "European")
                existing_df.at[last_row_idx, "food_preferences_american_latin"] = self._extract_specific_cuisine(user_preferences, "American/Latin")
                existing_df.at[last_row_idx, "food_preferences_middle_eastern"] = self._extract_specific_cuisine(user_preferences, "Middle Eastern")
                existing_df.at[last_row_idx, "food_preferences_african"] = self._extract_specific_cuisine(user_preferences, "African")
                existing_df.at[last_row_idx, "food_preferences_caribbean"] = self._extract_specific_cuisine(user_preferences, "Caribbean")
                existing_df.at[last_row_idx, "food_preferences_local_cuisine"] = self._extract_specific_cuisine(user_preferences, "Local Cuisine")
                
                # 更新酒店偏好
                existing_df.at[last_row_idx, "hotel_preferences"] = self._extract_hotel_preferences(user_preferences)
                
                logger.info(f"Updated preferences for row {last_row_idx}")
            else:
                # If there are somehow no rows after the previous checks, add a new row
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                new_row = {
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "origin": user_preferences.get("origin", ""),
                    "destination": user_preferences.get("destination", ""),
                    "arrival_time": user_preferences.get("arrival_time", ""),
                    "departure_time": user_preferences.get("departure_time", ""),
                    "cabin_type": user_preferences.get("cabin_type", "ECONOMY"),
                    # 添加详细的偏好字段
                    "activity_interests_cultural": self._extract_specific_interest(user_preferences, "Cultural"),
                    "activity_interests_nature_outdoors": self._extract_specific_interest(user_preferences, "Nature & Outdoors"),
                    "activity_interests_entertainment": self._extract_specific_interest(user_preferences, "Entertainment"),
                    "activity_interests_shopping": self._extract_specific_interest(user_preferences, "Shopping"),
                    "activity_interests_recreation": self._extract_specific_interest(user_preferences, "Recreation"),
                    "activity_interests_nightlife": self._extract_specific_interest(user_preferences, "Nightlife"),
                    # 食物偏好
                    "food_preferences_asian": self._extract_specific_cuisine(user_preferences, "Asian"),
                    "food_preferences_european": self._extract_specific_cuisine(user_preferences, "European"),
                    "food_preferences_american_latin": self._extract_specific_cuisine(user_preferences, "American/Latin"),
                    "food_preferences_middle_eastern": self._extract_specific_cuisine(user_preferences, "Middle Eastern"),
                    "food_preferences_african": self._extract_specific_cuisine(user_preferences, "African"),
                    "food_preferences_caribbean": self._extract_specific_cuisine(user_preferences, "Caribbean"),
                    "food_preferences_local_cuisine": self._extract_specific_cuisine(user_preferences, "Local Cuisine"),
                    # 酒店偏好
                    "hotel_preferences": self._extract_hotel_preferences(user_preferences)
                }
                # Append the new row to the dataframe
                existing_df = pd.concat([existing_df, pd.DataFrame([new_row])], ignore_index=True)
                logger.info("Added new row with preferences")
            
            # Save updated dataframe back to CSV
            existing_df.to_csv(filename, index=False)
            logger.info(f"Saved updated dataframe to {filename}")
            
            # Verify the file was saved correctly
            if os.path.exists(filename) and os.path.getsize(filename) > 0:
                logger.info(f"Successfully updated temp file: {filename}")
                return filename
            else:
                logger.error(f"File verification failed after save: {filename}")
                return ""
            
        except Exception as e:
            logger.error(f"Error updating temp file with preferences: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return ""
    
    def save_recommendation(self, user_id: str, 
                           travel_plan: Dict[str, Any], 
                           user_feedback: str) -> str:
        """
        Save successful travel plans to recommend.csv for reference
        
        Args:
            user_id: User ID
            travel_plan: The finalized travel plan
            user_feedback: User feedback on the plan
            
        Returns:
            Path to the recommend file
        """
        user_dir = self._get_user_dir(user_id)
        filename = os.path.join(user_dir, "recommend.csv")
        
        # Current timestamp
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Basic plan data
        plan_data = {
            "timestamp": timestamp,
            "user_id": user_id,
            "destination": travel_plan.get("destination", ""),
            "departure_date": travel_plan.get("departure_date", ""),
            "return_date": travel_plan.get("return_date", ""),
            "user_feedback": user_feedback,
            "travel_plan": json.dumps(travel_plan)
        }
        
        # Check if file exists to append or create new
        if os.path.exists(filename):
            # Read existing data
            existing_df = pd.read_csv(filename)
            # Append new data
            updated_df = pd.concat([existing_df, pd.DataFrame([plan_data])], ignore_index=True)
            updated_df.to_csv(filename, index=False)
        else:
            # Create new file
            pd.DataFrame([plan_data]).to_csv(filename, index=False)
            
        return filename
    
    def get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get user recommendation history from recommend.csv
        
        Args:
            user_id: User ID
            
        Returns:
            List of user's previous travel plans
        """
        user_dir = self._get_user_dir(user_id)
        recommend_file = os.path.join(user_dir, "recommend.csv")
        
        if not os.path.exists(recommend_file):
            return []
            
        try:
            # Read the CSV file
            df = pd.read_csv(recommend_file)
            if df.empty:
                return []
                
            # Convert to list of dictionaries
            history = []
            for _, row in df.iterrows():
                item = row.to_dict()
                # Parse JSON fields
                if "travel_plan" in item:
                    try:
                        item["travel_plan"] = json.loads(item["travel_plan"])
                    except:
                        pass
                history.append(item)
            
            # Sort by timestamp (newest first)
            history.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return history
        except Exception as e:
            print(f"Error reading recommend file: {str(e)}")
            return []
    
    def get_flight_data_as_json(self, user_id: str) -> Dict[str, Any]:
        """
        读取用户的temp.csv文件并将航班数据转换为JSON格式
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含航班关键信息的JSON数据字典
        """
        user_dir = self._get_user_dir(user_id)
        temp_file = os.path.join(user_dir, "temp.csv")
        
        # 检查文件是否存在
        if not os.path.exists(temp_file):
            logger.warning(f"临时文件不存在: {temp_file}")
            return {
                "origin": "",
                "destination": "",
                "arrival_time": "",
                "departure_time": "",
                "cabin_type": ""
            }
        
        try:
            # 读取CSV文件
            df = pd.read_csv(temp_file)
            if df.empty:
                logger.warning(f"临时文件为空: {temp_file}")
                return {
                    "origin": "",
                    "destination": "",
                    "arrival_time": "",
                    "departure_time": "",
                    "cabin_type": ""
                }
            
            # 获取最新的条目
            latest_entry = df.iloc[-1].to_dict()
            
            # 提取需要的字段
            flight_data = {
                "origin": latest_entry.get("origin", ""),
                "destination": latest_entry.get("destination", ""),
                "arrival_time": latest_entry.get("arrival_time", ""),
                "departure_time": latest_entry.get("departure_time", ""),
                "cabin_type": latest_entry.get("cabin_type", "")
            }
            
            # 如果有，提取时间戳
            if "timestamp" in latest_entry:
                flight_data["timestamp"] = latest_entry["timestamp"]
            
            logger.info(f"成功从CSV中提取航班数据为JSON格式: {json.dumps(flight_data)}")
            return flight_data
            
        except Exception as e:
            logger.error(f"读取临时文件错误: {str(e)}")
            import traceback
            logger.error(f"错误详情: {traceback.format_exc()}")
            return {
                "origin": "",
                "destination": "",
                "arrival_time": "",
                "departure_time": "",
                "cabin_type": ""
            }
    
    def _extract_activity_interests(self, user_preferences: Dict[str, Any]) -> str:
        """
        从用户偏好中提取活动兴趣
        """
        # 尝试从travel_preferences中提取
        if "travel_preferences" in user_preferences and isinstance(user_preferences["travel_preferences"], dict):
            if "activity_interests" in user_preferences["travel_preferences"]:
                interests = user_preferences["travel_preferences"]["activity_interests"]
                if isinstance(interests, list):
                    return ", ".join(interests)
                return str(interests)
        
        # 尝试从activity_categories中提取
        if "activity_categories" in user_preferences and isinstance(user_preferences["activity_categories"], list):
            return ", ".join(user_preferences["activity_categories"])
        
        return ""
    
    def _extract_hotel_preferences(self, user_preferences: Dict[str, Any]) -> str:
        """
        从用户偏好中提取酒店偏好
        """
        # 打印用户偏好，帮助调试
        logger.info(f"提取酒店偏好，用户偏好: {user_preferences.get('travel_preferences', {}).get('hotel_preference', '')}")
        logger.info(f"hotel_price_level: {user_preferences.get('hotel_price_level', '')}")
        
        # 尝试从travel_preferences中提取
        if "travel_preferences" in user_preferences and isinstance(user_preferences["travel_preferences"], dict):
            if "hotel_preference" in user_preferences["travel_preferences"]:
                hotel_pref = str(user_preferences["travel_preferences"]["hotel_preference"])
                logger.info(f"从travel_preferences中提取到酒店偏好: {hotel_pref}")
                return hotel_pref
        
        # 尝试从hotel_price_level中提取
        if "hotel_price_level" in user_preferences:
            hotel_pref = str(user_preferences["hotel_price_level"])
            logger.info(f"从hotel_price_level中提取到酒店偏好: {hotel_pref}")
            return hotel_pref
            
        # 尝试从hotel_preference中提取（可能的直接键）
        if "hotel_preference" in user_preferences:
            hotel_pref = str(user_preferences["hotel_preference"])
            logger.info(f"从hotel_preference中提取到酒店偏好: {hotel_pref}")
            return hotel_pref
        
        logger.warning("未找到酒店偏好")
        return ""
    
    def _extract_food_preferences(self, user_preferences: Dict[str, Any]) -> str:
        """
        从用户偏好中提取食物偏好 - 只提取cuisine regions
        """
        # 尝试从travel_preferences中提取
        if "travel_preferences" in user_preferences and isinstance(user_preferences["travel_preferences"], dict):
            # 提取美食区域
            if "cuisine_regions" in user_preferences["travel_preferences"]:
                cuisines = user_preferences["travel_preferences"]["cuisine_regions"]
                if isinstance(cuisines, list):
                    return ", ".join(cuisines)
                return str(cuisines)
        
        # 尝试从cuisine_regions直接提取
        if "cuisine_regions" in user_preferences and isinstance(user_preferences["cuisine_regions"], list):
            return ", ".join(user_preferences["cuisine_regions"])
        
        return ""
    
    def _extract_specific_interest(self, user_preferences: Dict[str, Any], interest_type: str) -> str:
        """
        从用户偏好中提取特定类型的活动兴趣
        
        Args:
            user_preferences: 用户偏好字典
            interest_type: 兴趣类型，如"Cultural"、"Nature & Outdoors"等
            
        Returns:
            如果用户选择了该类型的兴趣，返回"1"，否则返回"0"
        """
        # 打印当前处理的兴趣类型和用户偏好，帮助调试
        logger.info(f"提取活动兴趣: {interest_type}, 用户偏好: {user_preferences.get('travel_preferences', {}).get('activity_interests', [])}")
        
        # 尝试从travel_preferences中提取
        if "travel_preferences" in user_preferences and isinstance(user_preferences["travel_preferences"], dict):
            if "activity_interests" in user_preferences["travel_preferences"]:
                interests = user_preferences["travel_preferences"]["activity_interests"]
                if isinstance(interests, list):
                    # 精确匹配兴趣类型
                    if interest_type in interests:
                        logger.info(f"找到匹配的兴趣: {interest_type}")
                        return "1"  # 表示用户选择了该兴趣类型
        
        # 尝试从activity_categories中提取
        if "activity_categories" in user_preferences and isinstance(user_preferences["activity_categories"], list):
            # 精确匹配兴趣类型
            if interest_type in user_preferences["activity_categories"]:
                logger.info(f"在activity_categories中找到匹配的兴趣: {interest_type}")
                return "1"  # 表示用户选择了该兴趣类型
        
        return "0"  # 表示用户未选择该兴趣类型
    
    def _extract_specific_cuisine(self, user_preferences: Dict[str, Any], cuisine_type: str) -> str:
        """
        从用户偏好中提取特定类型的食物偏好
        
        Args:
            user_preferences: 用户偏好字典
            cuisine_type: 美食类型，如"Asian"、"European"等
            
        Returns:
            如果用户选择了该类型的美食，返回"1"，否则返回"0"
        """
        # 打印当前处理的美食类型和用户偏好，帮助调试
        logger.info(f"提取美食偏好: {cuisine_type}, 用户偏好: {user_preferences.get('travel_preferences', {}).get('cuisine_regions', [])}")
        
        # 尝试从travel_preferences中提取
        if "travel_preferences" in user_preferences and isinstance(user_preferences["travel_preferences"], dict):
            if "cuisine_regions" in user_preferences["travel_preferences"]:
                cuisines = user_preferences["travel_preferences"]["cuisine_regions"]
                if isinstance(cuisines, list):
                    # 精确匹配美食类型
                    if cuisine_type in cuisines:
                        logger.info(f"找到匹配的美食: {cuisine_type}")
                        return "1"  # 表示用户选择了该美食类型
        
        # 尝试从cuisine_regions直接提取
        if "cuisine_regions" in user_preferences and isinstance(user_preferences["cuisine_regions"], list):
            # 精确匹配美食类型
            if cuisine_type in user_preferences["cuisine_regions"]:
                logger.info(f"在cuisine_regions中找到匹配的美食: {cuisine_type}")
                return "1"  # 表示用户选择了该美食类型
        
        return "0"  # 表示用户未选择该美食类型 