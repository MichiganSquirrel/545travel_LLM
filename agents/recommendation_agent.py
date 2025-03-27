import json
import os
from typing import Dict, List, Any, Optional
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from models.clustering_model import ClusteringModel
from database.db_manager import DatabaseManager

class RecommendationAgent:
    def __init__(self, database_manager: DatabaseManager, api_key: Optional[str] = None):
        self.llm = OpenAI(temperature=0.7, api_key=api_key)
        self.database_manager = database_manager
        self.clustering_model = ClusteringModel()
        
        # 推荐生成模板
        self.recommendation_template = """
        请基于用户的旅行计划和偏好，生成个性化的旅行推荐。

        当前旅行计划：
        {travel_plan}

        用户偏好：
        {user_preferences}

        相似的历史旅行：
        {similar_trips}

        请提供以下方面的建议：
        1. 最适合用户的3-5家酒店，包括名称、星级和简短描述
        2. 最符合用户口味的4-6家餐厅，包括名称、菜系和特色
        3. 最符合用户兴趣的5-8个景点/活动，包括名称和亮点
        4. 根据用户的历史旅行模式，提供1-2条关于行程安排的建议

        请以JSON格式返回，格式如下：
        {
          "hotels": [{"name": "酒店名称", "stars": "星级", "description": "简短描述"}],
          "restaurants": [{"name": "餐厅名称", "cuisine": "菜系", "highlights": "特色"}],
          "attractions": [{"name": "景点名称", "highlights": "亮点"}],
          "suggestions": ["行程建议1", "行程建议2"]
        }
        """
        
    def generate_recommendations(self, user_id: str, travel_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成基于用户偏好和历史的个性化旅行推荐
        
        参数:
            user_id: 用户ID
            travel_plan: 当前旅行计划
            
        返回:
            个性化旅行推荐
        """
        # 获取用户目录
        user_dir = self.database_manager.get_user_directory(user_id)
        
        # 获取用户偏好
        user_preferences = self.database_manager.get_user_preferences(user_id)
        
        # 获取相似的旅行计划
        recommendations_path = os.path.join(user_dir, "recommendations.csv")
        similar_trips = self.clustering_model.find_similar_trips(travel_plan, recommendations_path)
        
        prompt = PromptTemplate(
            input_variables=["travel_plan", "user_preferences", "similar_trips"],
            template=self.recommendation_template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # 准备输入数据
        preferences_text = self._format_preferences(user_preferences)
        similar_trips_text = self._format_similar_trips(similar_trips)
        
        # 生成推荐
        try:
            recommendations_json = chain.run(
                travel_plan=json.dumps(travel_plan, ensure_ascii=False),
                user_preferences=preferences_text,
                similar_trips=similar_trips_text
            )
            
            recommendations = json.loads(recommendations_json)
            
            # 保存推荐结果
            if travel_plan.get("destination") and travel_plan.get("start_date") and travel_plan.get("end_date"):
                self.database_manager.save_recommendation(
                    user_id=user_id,
                    destination=travel_plan["destination"],
                    start_date=travel_plan["start_date"],
                    end_date=travel_plan["end_date"],
                    plan=recommendations
                )
            
            return recommendations
        except Exception as e:
            print(f"生成推荐时出错: {str(e)}")
            return {
                "hotels": ["推荐生成失败"],
                "restaurants": ["推荐生成失败"],
                "attractions": ["推荐生成失败"],
                "suggestions": [f"推荐生成失败: {str(e)}"]
            }
            
    def _format_preferences(self, preferences: List[Dict[str, Any]]) -> str:
        """
        将用户偏好格式化为文本
        
        参数:
            preferences: 用户偏好列表
            
        返回:
            格式化的偏好文本
        """
        if not preferences:
            return "用户没有明确的偏好记录。"
            
        # 按偏好类型分组
        grouped_prefs = {}
        for pref in preferences:
            pref_type = pref.get("preference_type")
            if pref_type not in grouped_prefs:
                grouped_prefs[pref_type] = []
            grouped_prefs[pref_type].append(pref)
        
        # 格式化文本
        result = []
        for pref_type, prefs in grouped_prefs.items():
            values = [f"{p.get('preference_value')} (置信度: {p.get('confidence_score'):.2f})" for p in prefs]
            result.append(f"{pref_type}: {', '.join(values)}")
        
        return "\n".join(result)
    
    def _format_similar_trips(self, similar_trips: List[Dict[str, Any]]) -> str:
        """
        将相似旅行计划格式化为文本
        
        参数:
            similar_trips: 相似旅行计划列表
            
        返回:
            格式化的相似旅行文本
        """
        if not similar_trips:
            return "没有找到相似的历史旅行计划。"
            
        result = []
        for i, trip in enumerate(similar_trips):
            result.append(f"相似旅行 {i+1}:")
            result.append(f"- 目的地: {trip.get('destination', '未知')}")
            result.append(f"- 日期: {trip.get('start_date', '未知')} 至 {trip.get('end_date', '未知')}")
            result.append(f"- 相似度: {trip.get('similarity_score', 0):.2f}")
            
            # 添加计划详情
            plan = trip.get("plan", {})
            if plan:
                if "hotels" in plan:
                    hotels = plan["hotels"]
                    if isinstance(hotels, list) and hotels:
                        if isinstance(hotels[0], dict):
                            hotel_names = [h.get("name", "未知酒店") for h in hotels]
                        else:
                            hotel_names = hotels
                        result.append(f"- 酒店: {', '.join(hotel_names[:3])}")
                
                if "attractions" in plan:
                    attractions = plan["attractions"]
                    if isinstance(attractions, list) and attractions:
                        if isinstance(attractions[0], dict):
                            attraction_names = [a.get("name", "未知景点") for a in attractions]
                        else:
                            attraction_names = attractions
                        result.append(f"- 景点: {', '.join(attraction_names[:3])}")
            
            result.append("")  # 添加空行分隔
        
        return "\n".join(result)
    
    def analyze_travel_patterns(self, user_id: str) -> Dict[str, Any]:
        """
        分析用户的旅行模式
        
        参数:
            user_id: 用户ID
            
        返回:
            旅行模式分析结果
        """
        user_dir = self.database_manager.get_user_directory(user_id)
        recommendations_path = os.path.join(user_dir, "recommendations.csv")
        
        return self.clustering_model.analyze_user_patterns(recommendations_path)
    
    def generate_detailed_plan(self, user_id: str, travel_query: Dict[str, Any]) -> Dict[str, Any]:
        """
        为用户生成详细的旅行计划
        
        参数:
            user_id: 用户ID
            travel_query: 旅行查询参数
            
        返回:
            详细的旅行计划
        """
        # 获取用户偏好
        user_preferences = self.database_manager.get_user_preferences(user_id)
        
        # 获取之前生成的推荐
        user_dir = self.database_manager.get_user_directory(user_id)
        temp_data = self.database_manager.get_temp_data(user_id)
        recommendations = self.database_manager.get_user_recommendations(user_id)
        
        # 详细计划生成模板
        detailed_plan_template = """
        请基于以下信息，为用户生成详细的旅行计划。

        旅行信息：
        {travel_query}

        用户偏好：
        {user_preferences}

        之前的推荐：
        {recommendations}

        请生成一个详细的旅行计划，包括：
        1. 每天的活动安排，包括时间、地点和活动内容
        2. 交通安排
        3. 用餐安排
        4. 必要的提示和注意事项

        请以JSON格式返回，格式如下：
        {
          "destination": "目的地",
          "start_date": "开始日期",
          "end_date": "结束日期",
          "summary": "行程概述",
          "daily_plan": {
            "day1": [
              {"time": "时间", "activity": "活动", "place": "地点", "notes": "备注"}
            ],
            "day2": [
              {"time": "时间", "activity": "活动", "place": "地点", "notes": "备注"}
            ]
          },
          "transportation": ["交通安排1", "交通安排2"],
          "tips": ["提示1", "提示2"]
        }
        """
        
        prompt = PromptTemplate(
            input_variables=["travel_query", "user_preferences", "recommendations"],
            template=detailed_plan_template
        )
        
        chain = LLMChain(llm=self.llm, prompt=prompt)
        
        # 准备输入数据
        preferences_text = self._format_preferences(user_preferences)
        recommendations_text = self._format_recommendations(recommendations)
        
        # 生成详细计划
        try:
            plan_json = chain.run(
                travel_query=json.dumps(travel_query, ensure_ascii=False),
                user_preferences=preferences_text,
                recommendations=recommendations_text
            )
            
            detailed_plan = json.loads(plan_json)
            
            # 保存计划
            if "destination" in detailed_plan and "start_date" in detailed_plan and "end_date" in detailed_plan:
                self.database_manager.save_recommendation(
                    user_id=user_id,
                    destination=detailed_plan["destination"],
                    start_date=detailed_plan["start_date"],
                    end_date=detailed_plan["end_date"],
                    plan=detailed_plan
                )
            
            return detailed_plan
        except Exception as e:
            print(f"生成详细计划时出错: {str(e)}")
            return {
                "error": f"生成详细计划失败: {str(e)}",
                "destination": travel_query.get("destination", "未知"),
                "daily_plan": {"day1": [{"time": "全天", "activity": "计划生成失败", "place": "", "notes": ""}]}
            }
    
    def _format_recommendations(self, recommendations: List[Dict[str, Any]]) -> str:
        """
        将推荐历史格式化为文本
        
        参数:
            recommendations: 推荐历史列表
            
        返回:
            格式化的推荐文本
        """
        if not recommendations:
            return "没有找到历史推荐记录。"
            
        # 只使用最近的3个推荐
        recent_recommendations = recommendations[:3]
        
        result = []
        for i, rec in enumerate(recent_recommendations):
            result.append(f"历史推荐 {i+1}:")
            result.append(f"- 目的地: {rec.get('destination', '未知')}")
            result.append(f"- 日期: {rec.get('start_date', '未知')} 至 {rec.get('end_date', '未知')}")
            
            # 添加计划详情
            plan = rec.get("plan", {})
            if plan:
                if "hotels" in plan:
                    hotels = plan["hotels"]
                    if isinstance(hotels, list) and hotels:
                        if isinstance(hotels[0], dict):
                            hotel_names = [h.get("name", "未知酒店") for h in hotels]
                        else:
                            hotel_names = hotels
                        result.append(f"- 酒店: {', '.join(hotel_names[:3])}")
                
                if "attractions" in plan:
                    attractions = plan["attractions"]
                    if isinstance(attractions, list) and attractions:
                        if isinstance(attractions[0], dict):
                            attraction_names = [a.get("name", "未知景点") for a in attractions]
                        else:
                            attraction_names = attractions
                        result.append(f"- 景点: {', '.join(attraction_names[:3])}")
                
                if "daily_plan" in plan:
                    result.append("- 行程安排:")
                    for day, activities in plan["daily_plan"].items():
                        day_summary = []
                        for activity in activities[:2]:  # 只显示前两个活动
                            if isinstance(activity, dict):
                                day_summary.append(activity.get("activity", "未知活动"))
                            else:
                                day_summary.append(str(activity))
                        result.append(f"  * {day}: {', '.join(day_summary)}...")
            
            result.append("")  # 添加空行分隔
        
        return "\n".join(result) 