import pandas as pd
import numpy as np
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from typing import Dict, List, Any, Optional, Tuple

class ClusteringModel:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
    
    def find_similar_trips(self, current_plan: Dict[str, Any], recommendations_csv: str, top_n: int = 3) -> List[Dict[str, Any]]:
        """
        根据文本相似度从推荐历史中查找相似的旅行计划
        
        参数:
            current_plan: 当前旅行计划
            recommendations_csv: 包含历史推荐的CSV文件路径
            top_n: 返回的相似计划数量
            
        返回:
            相似旅行计划的列表
        """
        # 检查文件是否存在
        if not os.path.exists(recommendations_csv):
            return []
        
        # 加载历史数据
        try:
            df = pd.read_csv(recommendations_csv)
            if df.empty:
                return []
                
            # 解析JSON字段
            df['plan_json'] = df['plan_json'].apply(lambda x: self._safe_json_loads(x))
            
            # 提取文本特征
            current_plan_text = self._extract_text_features(current_plan)
            history_texts = df['plan_json'].apply(lambda x: self._extract_text_features(x)).tolist()
            
            if not history_texts:
                return []
                
            # 计算相似度
            similarities, top_indices = self._calculate_similarities(current_plan_text, history_texts, top_n)
            
            # 构建返回结果
            results = []
            for i, idx in enumerate(top_indices):
                if idx < len(df):
                    row = df.iloc[idx]
                    result = {
                        "destination": row["destination"],
                        "start_date": row["start_date"],
                        "end_date": row["end_date"],
                        "plan": row["plan_json"],
                        "similarity_score": float(similarities[i])
                    }
                    results.append(result)
            
            return results
        except Exception as e:
            print(f"查找相似旅行计划时出错: {str(e)}")
            return []
    
    def _safe_json_loads(self, json_str) -> Dict:
        """安全地解析JSON字符串，出错时返回空字典"""
        if not json_str or not isinstance(json_str, str):
            return {}
        try:
            import json
            return json.loads(json_str)
        except:
            return {}
    
    def _calculate_similarities(self, query_text: str, corpus_texts: List[str], top_n: int) -> Tuple[np.ndarray, np.ndarray]:
        """
        计算查询文本与语料库文本之间的相似度
        
        参数:
            query_text: 查询文本
            corpus_texts: 语料库文本列表
            top_n: 返回的相似文本数量
            
        返回:
            (相似度得分数组, 相似文本索引数组)
        """
        # 创建组合语料库
        all_texts = [query_text] + corpus_texts
        
        # 拟合和转换向量化器
        try:
            tfidf_matrix = self.vectorizer.fit_transform(all_texts)
            
            # 计算当前计划与所有历史计划之间的相似度
            similarities = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()
            
            # 获取相似度最高的计划索引
            if len(similarities) <= top_n:
                top_indices = np.argsort(similarities)[::-1]
                return similarities[top_indices], top_indices
            else:
                top_indices = np.argsort(similarities)[-top_n:][::-1]
                return similarities[top_indices], top_indices
        except:
            # 如果向量化失败，返回空结果
            return np.array([]), np.array([])
    
    def _extract_text_features(self, plan: Dict[str, Any]) -> str:
        """
        从旅行计划中提取文本特征
        
        参数:
            plan: 旅行计划字典
            
        返回:
            文本特征字符串
        """
        if not plan or not isinstance(plan, dict):
            return ""
            
        text_features = []
        
        # 提取目的地
        if "destination" in plan:
            text_features.append(str(plan["destination"]))
        
        # 提取酒店信息
        if "hotels" in plan:
            hotels = plan["hotels"]
            if isinstance(hotels, list):
                for hotel in hotels:
                    if isinstance(hotel, dict):
                        text_features.append(str(hotel.get("name", "")))
                        text_features.append(str(hotel.get("category", "")))
                    elif isinstance(hotel, str):
                        text_features.append(hotel)
            elif isinstance(hotels, str):
                text_features.append(hotels)
        
        # 提取景点信息
        if "attractions" in plan:
            attractions = plan["attractions"]
            if isinstance(attractions, list):
                for attraction in attractions:
                    if isinstance(attraction, dict):
                        text_features.append(str(attraction.get("name", "")))
                        text_features.append(str(attraction.get("category", "")))
                    elif isinstance(attraction, str):
                        text_features.append(attraction)
            elif isinstance(attractions, str):
                text_features.append(attractions)
        
        # 提取餐厅信息
        if "restaurants" in plan:
            restaurants = plan["restaurants"]
            if isinstance(restaurants, list):
                for restaurant in restaurants:
                    if isinstance(restaurant, dict):
                        text_features.append(str(restaurant.get("name", "")))
                        text_features.append(str(restaurant.get("cuisine", "")))
                    elif isinstance(restaurant, str):
                        text_features.append(restaurant)
            elif isinstance(restaurants, str):
                text_features.append(restaurants)
        
        # 提取活动信息
        if "activities" in plan:
            activities = plan["activities"]
            if isinstance(activities, list):
                for activity in activities:
                    if isinstance(activity, dict):
                        text_features.append(str(activity.get("name", "")))
                        text_features.append(str(activity.get("type", "")))
                    elif isinstance(activity, str):
                        text_features.append(activity)
            elif isinstance(activities, str):
                text_features.append(activities)
        
        # 提取详细计划
        if "detailed_plan" in plan:
            detailed_plan = plan["detailed_plan"]
            if isinstance(detailed_plan, dict):
                for day, day_plan in detailed_plan.items():
                    if isinstance(day_plan, list):
                        for item in day_plan:
                            if isinstance(item, dict):
                                text_features.append(str(item.get("activity", "")))
                                text_features.append(str(item.get("place", "")))
                            elif isinstance(item, str):
                                text_features.append(item)
                    elif isinstance(day_plan, str):
                        text_features.append(day_plan)
            elif isinstance(detailed_plan, str):
                text_features.append(detailed_plan)
        
        # 过滤空字符串并合并
        text_features = [feature for feature in text_features if feature and feature.strip()]
        return " ".join(text_features)
        
    def analyze_user_patterns(self, recommendations_csv: str) -> Dict[str, Any]:
        """
        分析用户的旅行模式和偏好
        
        参数:
            recommendations_csv: 包含历史推荐的CSV文件路径
            
        返回:
            用户旅行模式分析结果
        """
        if not os.path.exists(recommendations_csv):
            return {"error": "推荐历史文件不存在"}
            
        try:
            df = pd.read_csv(recommendations_csv)
            if df.empty:
                return {"error": "推荐历史为空"}
                
            # 初始化结果字典
            analysis = {
                "total_trips": len(df),
                "favorite_destinations": {},
                "average_trip_duration": 0,
                "travel_seasons": {"spring": 0, "summer": 0, "fall": 0, "winter": 0}
            }
            
            # 分析目的地偏好
            if "destination" in df.columns:
                destination_counts = df["destination"].value_counts().to_dict()
                analysis["favorite_destinations"] = destination_counts
            
            # 分析行程时长
            if "start_date" in df.columns and "end_date" in df.columns:
                df["start_date"] = pd.to_datetime(df["start_date"], errors="coerce")
                df["end_date"] = pd.to_datetime(df["end_date"], errors="coerce")
                df["duration"] = (df["end_date"] - df["start_date"]).dt.days
                analysis["average_trip_duration"] = df["duration"].mean()
                
                # 分析旅行季节
                df["month"] = df["start_date"].dt.month
                for _, row in df.iterrows():
                    month = row["month"]
                    if month in [3, 4, 5]:  # 春季
                        analysis["travel_seasons"]["spring"] += 1
                    elif month in [6, 7, 8]:  # 夏季
                        analysis["travel_seasons"]["summer"] += 1
                    elif month in [9, 10, 11]:  # 秋季
                        analysis["travel_seasons"]["fall"] += 1
                    else:  # 冬季
                        analysis["travel_seasons"]["winter"] += 1
            
            return analysis
        except Exception as e:
            return {"error": f"分析用户旅行模式时出错: {str(e)}"}
            
    def cluster_users(self, all_recommendations_csv: str, n_clusters: int = 3) -> Dict[str, Any]:
        """
        对用户进行聚类分析，找出相似用户群体
        
        参数:
            all_recommendations_csv: 包含所有用户推荐的CSV文件路径
            n_clusters: 聚类数量
            
        返回:
            用户聚类结果
        """
        # 此功能需要scikit-learn的额外组件
        try:
            from sklearn.cluster import KMeans
            
            if not os.path.exists(all_recommendations_csv):
                return {"error": "推荐历史文件不存在"}
                
            df = pd.read_csv(all_recommendations_csv)
            if df.empty or "user_id" not in df.columns:
                return {"error": "推荐历史为空或缺少用户ID"}
                
            # 提取用户特征
            user_features = {}
            for user_id, user_df in df.groupby("user_id"):
                # 获取用户的目的地偏好
                destination_counts = user_df["destination"].value_counts().to_dict()
                
                # 计算平均行程时长
                user_df["start_date"] = pd.to_datetime(user_df["start_date"], errors="coerce")
                user_df["end_date"] = pd.to_datetime(user_df["end_date"], errors="coerce")
                user_df["duration"] = (user_df["end_date"] - user_df["start_date"]).dt.days
                avg_duration = user_df["duration"].mean()
                
                # 提取季节偏好
                user_df["month"] = user_df["start_date"].dt.month
                seasons = {"spring": 0, "summer": 0, "fall": 0, "winter": 0}
                for _, row in user_df.iterrows():
                    month = row["month"]
                    if month in [3, 4, 5]:  # 春季
                        seasons["spring"] += 1
                    elif month in [6, 7, 8]:  # 夏季
                        seasons["summer"] += 1
                    elif month in [9, 10, 11]:  # 秋季
                        seasons["fall"] += 1
                    else:  # 冬季
                        seasons["winter"] += 1
                
                # 组合用户特征
                user_features[user_id] = {
                    "destinations": destination_counts,
                    "avg_duration": avg_duration,
                    "seasons": seasons
                }
            
            # 将特征转换为向量
            feature_matrix = []
            user_ids = []
            
            for user_id, features in user_features.items():
                user_vector = [
                    features["avg_duration"],
                    features["seasons"]["spring"],
                    features["seasons"]["summer"],
                    features["seasons"]["fall"],
                    features["seasons"]["winter"]
                ]
                
                # 添加目的地向量（简化处理）
                for dest, count in features["destinations"].items():
                    user_vector.append(count)
                
                feature_matrix.append(user_vector)
                user_ids.append(user_id)
            
            # 确保所有向量长度相同（填充0）
            max_length = max(len(v) for v in feature_matrix)
            feature_matrix = [v + [0] * (max_length - len(v)) for v in feature_matrix]
            
            # 执行K-means聚类
            kmeans = KMeans(n_clusters=min(n_clusters, len(feature_matrix)))
            clusters = kmeans.fit_predict(feature_matrix)
            
            # 组织结果
            result = {"clusters": {}}
            for i, cluster_id in enumerate(clusters):
                cluster_id = int(cluster_id)
                user_id = user_ids[i]
                
                if cluster_id not in result["clusters"]:
                    result["clusters"][cluster_id] = []
                    
                result["clusters"][cluster_id].append({
                    "user_id": user_id,
                    "features": user_features[user_id]
                })
            
            return result
        except Exception as e:
            return {"error": f"聚类分析时出错: {str(e)}"} 