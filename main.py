import os
import json
from datetime import datetime
from agents.langchain_agent import TravelPlannerAgent
from agents.data_processor import DataProcessor
from agents.recommendation_agent import RecommendationAgent 
from api.flight_api import FlightAPI
from api.hotel_api import HotelAPI
from api.restaurant_api import RestaurantAPI
from api.attraction_api import AttractionAPI
from database.db_manager import DatabaseManager
from models.supervision_model import SupervisionModel
from config import load_api_keys

class TravelRecommendationSystem:
    def __init__(self):
        # 加载API密钥
        load_api_keys()
        
        # 初始化数据库管理器
        self.db_manager = DatabaseManager()
        
        # 初始化代理
        self.travel_agent = TravelPlannerAgent()
        self.data_processor = DataProcessor()
        self.recommendation_agent = RecommendationAgent(self.db_manager)
        self.supervision_model = SupervisionModel()
        
        # 初始化API客户端
        self.flight_api = FlightAPI()
        self.hotel_api = HotelAPI()
        self.restaurant_api = RestaurantAPI()
        self.attraction_api = AttractionAPI()
    
    def process_travel_query(self, user_id: str, user_query: dict):
        """处理用户的旅行查询"""
        try:
            # 确保user_query是字典类型
            if isinstance(user_query, str):
                try:
                    user_query = json.loads(user_query)
                except:
                    user_query = {"query": user_query}
            
            # 保存会话历史
            conversation = [{"speaker": "user", "message": user_query}]
            
            # 获取用户当前的记忆库
            user_dir = self.db_manager.get_user_directory(user_id)
            memory_bank_path = os.path.join(user_dir, "memory_bank.csv")
            current_preferences = self.supervision_model.load_from_csv(memory_bank_path)
            
            # 分析对话并更新用户偏好
            updated_preferences = self.supervision_model.analyze_conversation(conversation, current_preferences)
            
            # 保存更新后的偏好
            if updated_preferences:
                for pref in updated_preferences:
                    if "preference_type" in pref and "preference_value" in pref:
                        self.db_manager.save_user_preference(
                            user_id=user_id,
                            preference_type=pref.get("preference_type", "unknown"),
                            preference_value=pref.get("preference_value", ""),
                            confidence_score=pref.get("confidence_score", 0.5)
                        )
            
            # 查询航班数据
            flight_data = self.flight_api.search_flights(
                origin=user_query.get('origin'),
                destination=user_query.get('destination'),
                departure_date=user_query.get('departure_date'),
                return_date=user_query.get('return_date')
            )
            
            # 保存临时航班数据
            self.db_manager.save_temp_data(user_id, "flight", flight_data)
            
            # 查询酒店数据
            hotel_data = self.hotel_api.search_hotels(
                location=user_query.get('destination'),
                check_in=user_query.get('departure_date'),
                check_out=user_query.get('return_date')
            )
            
            # 保存临时酒店数据
            self.db_manager.save_temp_data(user_id, "hotel", hotel_data)
            
            # 查询餐厅数据
            restaurant_data = self.restaurant_api.search_restaurants(
                location=user_query.get('destination')
            )
            
            # 保存临时餐厅数据
            self.db_manager.save_temp_data(user_id, "restaurant", restaurant_data)
            
            # 查询景点数据
            attraction_data = self.attraction_api.search_attractions(
                location=user_query.get('destination')
            )
            
            # 保存临时景点数据
            self.db_manager.save_temp_data(user_id, "attraction", attraction_data)
            
            # 处理API数据
            processed_data = {
                "flight_data": self.data_processor.process_flight_data(flight_data),
                "hotel_data": self.data_processor.process_hotel_data(hotel_data),
                "restaurant_data": self.data_processor.process_restaurant_data(restaurant_data),
                "attraction_data": self.data_processor.process_attraction_data(attraction_data),
                "user_query": user_query
            }
            
            # 生成旅行建议
            recommendations = self.travel_agent.process_query(processed_data)
            
            # 确保recommendations是字典类型
            if not isinstance(recommendations, dict):
                if isinstance(recommendations, str):
                    try:
                        recommendations = json.loads(recommendations)
                    except:
                        recommendations = {"error": "无法解析推荐结果"}
                else:
                    recommendations = {"error": "未知推荐结果类型"}
            
            # 保存旅行建议
            travel_plan = {
                "destination": user_query.get('destination'),
                "start_date": user_query.get('departure_date'),
                "end_date": user_query.get('return_date'),
                "budget": user_query.get('budget'),
                "interests": user_query.get('interests', []),
                "recommendations": recommendations
            }
            
            # 生成个性化推荐
            personalized_recommendations = self.recommendation_agent.generate_recommendations(user_id, travel_plan)
            
            # 合并结果
            result = {
                "status": "success",
                "recommendations": recommendations,
                "personalized_recommendations": personalized_recommendations
            }
            
            # 保存系统回复到对话历史
            conversation.append({"speaker": "system", "message": result})
            
            return result
            
        except Exception as e:
            error_message = f"处理旅行查询时出错: {str(e)}"
            print(error_message)
            return {
                "status": "error",
                "message": error_message
            }
    
    def generate_detailed_plan(self, user_id: str, user_query: dict, selected_option: dict):
        """根据用户选择的选项生成详细计划"""
        try:
            # 确保输入都是字典类型
            if isinstance(user_query, str):
                try:
                    user_query = json.loads(user_query)
                except:
                    user_query = {"query": user_query}
                    
            if isinstance(selected_option, str):
                try:
                    selected_option = json.loads(selected_option)
                except:
                    selected_option = {"option": selected_option}
            
            # 保存用户选择
            self.db_manager.save_temp_data(user_id, "selected_option", selected_option)
            
            # 合并查询和选择
            travel_query = {**user_query, **selected_option}
            
            # 生成详细计划
            detailed_plan = self.recommendation_agent.generate_detailed_plan(user_id, travel_query)
            
            # 分析用户旅行模式
            travel_patterns = self.recommendation_agent.analyze_travel_patterns(user_id)
            
            return {
                "status": "success",
                "detailed_plan": detailed_plan,
                "travel_patterns": travel_patterns
            }
        except Exception as e:
            error_message = f"生成详细计划时出错: {str(e)}"
            print(error_message)
            return {
                "status": "error",
                "message": error_message
            }

def main():
    # 创建系统实例
    system = TravelRecommendationSystem()
    
    # 示例用户ID
    user_id = "user123"
    
    # 示例查询
    sample_query = {
        "origin": "北京",
        "destination": "上海",
        "departure_date": "2024-04-01",
        "return_date": "2024-04-05",
        "budget": "中等",
        "interests": ["文化", "美食", "购物"]
    }
    
    print("开始处理旅行查询...")
    
    # 处理查询
    result = system.process_travel_query(user_id, sample_query)
    
    # 打印结果
    if result["status"] == "success":
        print("\n推荐结果成功生成!")
        print(json.dumps(result["recommendations"], ensure_ascii=False, indent=2))
        
        # 模拟用户选择
        selected_option = {
            "selected_hotel": "上海和平饭店",  # 使用固定的酒店名称，避免索引错误
            "selected_attractions": ["外滩", "豫园", "上海博物馆"]  # 使用固定的景点名称
        }
        
        print("\n正在生成详细计划...")
        
        # 生成详细计划
        detailed_result = system.generate_detailed_plan(user_id, sample_query, selected_option)
        
        if detailed_result["status"] == "success":
            print("\n详细计划成功生成!")
            print(json.dumps(detailed_result["detailed_plan"], ensure_ascii=False, indent=2))
        else:
            print("\n生成详细计划失败:", detailed_result["message"])
    else:
        print("错误:", result["message"])
    
    print("\n数据已保存到用户目录:", os.path.join(system.db_manager.users_dir, user_id))

if __name__ == "__main__":
    main() 