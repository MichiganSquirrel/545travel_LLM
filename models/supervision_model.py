import json
import os
import pandas as pd
from typing import Dict, List, Any, Optional
from langchain_openai import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

class SupervisionModel:
    def __init__(self, api_key: Optional[str] = None):
        self.llm = OpenAI(temperature=0.2, api_key=api_key)
        
        # 偏好分析模板
        self.preference_template = """
        请分析以下对话内容，提取用户在旅行方面的偏好。
        
        对话内容：
        {conversation}
        
        当前已知的用户偏好：
        {current_preferences}
        
        分析要求：
        1. 提取用户明确表达的新偏好
        2. 对于与现有偏好冲突的新偏好，保留最新的偏好
        3. 对每个偏好赋予置信度分数(0.0-1.0)，直接陈述的偏好置信度较高，隐含的偏好置信度较低
        4. 将偏好分类为以下类型：destination(目的地)、cuisine(美食)、activity(活动)、accommodation(住宿)、transportation(交通)、budget(预算)、duration(行程时长)、season(季节)、travel_style(旅行风格)、companion(同伴类型)
        
        请以JSON格式返回提取的偏好，格式如下：
        [
            {"preference_type": "destination", "preference_value": "上海", "confidence_score": 0.9}
        ]
        
        如果没有提取到任何偏好，请返回空数组: []
        """
    
    def analyze_conversation(self, conversation: List[Dict[str, str]], current_memory_bank: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        分析对话提取和更新用户偏好
        
        参数:
            conversation: 对话内容列表，每项包含speaker和message
            current_memory_bank: 当前的记忆库内容
            
        返回:
            更新后的用户偏好列表
        """
        try:
            # 将对话格式化为文本
            conversation_text = ""
            for msg in conversation:
                # 检查message是否是字符串类型
                message = msg.get('message', '')
                if isinstance(message, dict):
                    message = json.dumps(message, ensure_ascii=False)
                
                speaker = "用户" if msg.get('speaker') == 'user' else "系统"
                conversation_text += f"{speaker}: {message}\n"
            
            # 格式化当前偏好
            current_preferences_text = ""
            for pref in current_memory_bank:
                current_preferences_text += f"- {pref.get('preference_type')}: {pref.get('preference_value')} (置信度: {pref.get('confidence_score')})\n"
            
            if not current_preferences_text:
                current_preferences_text = "暂无已知偏好"
            
            prompt = PromptTemplate(
                input_variables=["conversation", "current_preferences"],
                template=self.preference_template
            )
            
            chain = LLMChain(llm=self.llm, prompt=prompt)
            
            # 提取更新后的偏好
            try:
                updated_preferences_json = chain.run(
                    conversation=conversation_text,
                    current_preferences=current_preferences_text
                )
                
                # 清理JSON字符串，确保它是有效的JSON
                updated_preferences_json = updated_preferences_json.strip()
                if updated_preferences_json.startswith("```json"):
                    updated_preferences_json = updated_preferences_json.split("```json")[1]
                if updated_preferences_json.endswith("```"):
                    updated_preferences_json = updated_preferences_json.split("```")[0]
                
                updated_preferences = json.loads(updated_preferences_json)
                
                # 确保每个偏好都有必要的字段
                for pref in updated_preferences:
                    if "preference_type" not in pref:
                        pref["preference_type"] = "unknown"
                    if "preference_value" not in pref:
                        pref["preference_value"] = "未知"
                    if "confidence_score" not in pref:
                        pref["confidence_score"] = 0.5
                
                # 合并新旧偏好，保留最新和置信度最高的
                merged_preferences = self._merge_preferences(current_memory_bank, updated_preferences)
                
                return merged_preferences
            except Exception as e:
                print(f"提取偏好时出错: {str(e)}")
                # 遇到错误时返回一个空列表，而不是保持现有的记忆库
                return []
        except Exception as e:
            print(f"分析对话时出错: {str(e)}")
            return []
    
    def _merge_preferences(self, current_prefs: List[Dict[str, Any]], new_prefs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        合并新旧偏好，处理冲突
        
        参数:
            current_prefs: 当前偏好列表
            new_prefs: 新提取的偏好列表
            
        返回:
            合并后的偏好列表
        """
        # 创建一个字典，键为(偏好类型, 偏好值)对
        merged_dict = {}
        
        # 添加当前偏好
        for pref in current_prefs:
            if "preference_type" not in pref or "preference_value" not in pref:
                continue
                
            key = (pref.get('preference_type'), pref.get('preference_value'))
            merged_dict[key] = pref
        
        # 添加或覆盖新偏好
        for pref in new_prefs:
            if "preference_type" not in pref or "preference_value" not in pref:
                continue
                
            key = (pref.get('preference_type'), pref.get('preference_value'))
            
            # 如果是新偏好或置信度更高，则替换
            if key not in merged_dict or pref.get('confidence_score', 0) > merged_dict[key].get('confidence_score', 0):
                merged_dict[key] = pref
        
        # 转换回列表
        return list(merged_dict.values())
    
    def save_to_csv(self, preferences: List[Dict[str, Any]], csv_path: str) -> bool:
        """
        将分析的偏好保存到CSV文件
        
        参数:
            preferences: 偏好列表
            csv_path: CSV文件路径
            
        返回:
            是否成功保存
        """
        try:
            if not preferences:
                return True  # 如果没有偏好，视为成功
                
            df = pd.DataFrame(preferences)
            # 如果文件不存在，创建新文件并写入表头
            if not os.path.exists(csv_path):
                df.to_csv(csv_path, index=False)
            else:
                # 如果文件存在，追加数据不带表头
                df.to_csv(csv_path, mode='a', header=False, index=False)
            return True
        except Exception as e:
            print(f"保存偏好到CSV时出错: {str(e)}")
            return False
    
    def load_from_csv(self, csv_path: str) -> List[Dict[str, Any]]:
        """
        从CSV文件加载偏好
        
        参数:
            csv_path: CSV文件路径
            
        返回:
            加载的偏好列表
        """
        try:
            if os.path.exists(csv_path):
                df = pd.read_csv(csv_path)
                return df.to_dict('records')
            return []
        except Exception as e:
            print(f"从CSV加载偏好时出错: {str(e)}")
            return [] 