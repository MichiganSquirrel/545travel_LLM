import streamlit as st
import pandas as pd
import os
import json
import datetime

# Divider and section title
from utils import fix_existing_temp_file
st.set_page_config(
        page_title="User Preferences",
        page_icon="🛠️",
        initial_sidebar_state='collapsed'
 )
st.title("EECS 545 Travel Planner 🌏")
st.logo("images/TravelPlanner_Logo.png", icon_image="images/TravelPlanner_Logo.png")
st.subheader("🧭 Your Travel Preferences")

if "user_no" not in st.session_state or st.session_state.user_no==None:
    st.error("Please login to confirm preferences first")
    if st.button("Login", type="primary"):
        st.switch_page("app.py")


else:
    # Initialize session state for form persistence
    st.session_state.setdefault('activity_categories_selected', [])
    st.session_state.setdefault('hotel_price_level', "Medium")
    st.session_state.setdefault('cuisine_regions_selected', ["Local Cuisine"])

    preferences = {}

    # --- Preferences Form ---
    with st.form("Preferences Form"):
        st.write("### 🎯 Activity Interests")
        activity_categories = [
            "Cultural", 
            "Nature & Outdoors", 
            "Entertainment", 
            "Shopping", 
            "Recreation", 
            "Nightlife"
        ]
        selected_activity_categories = st.multiselect(
            "🎨 What kinds of activities are you into?",
            activity_categories,
            default=st.session_state.activity_categories_selected,
            key="activity_categories_widget"
        )

        st.write("### 🏨 Hotel Preferences")
        hotel_price_options = ["Budget", "Medium", "Luxury"]
        hotel_price_level = st.radio(
            "💰 Choose your comfort level:",
            options=hotel_price_options,
            horizontal=True,
            index=hotel_price_options.index(
                st.session_state.hotel_price_level if st.session_state.hotel_price_level in hotel_price_options else "Medium"
            ),
            key="hotel_price_widget"
        )

        st.write("### 🍽️ Cuisine Preferences")
        cuisine_regions = [
            "Asian", 
            "European", 
            "American/Latin", 
            "Middle Eastern",
            "African",
            "Caribbean",
            "Local Cuisine"
        ]
        selected_cuisine_regions = st.multiselect(
            "🍜 Which regional cuisines would you love to try?",
            cuisine_regions,
            default=st.session_state.cuisine_regions_selected,
            key="cuisine_regions_widget"
        )

        submitted = st.form_submit_button("✅ Save Preferences")

        if submitted:
            st.session_state.activity_categories_selected = selected_activity_categories
            st.session_state.hotel_price_level = hotel_price_level
            st.session_state.cuisine_regions_selected = selected_cuisine_regions
            st.success("🎉 Preferences saved in session!")
        

        # --- Process preferences ---
        if submitted or ('preferences' in st.session_state and st.session_state.preferences):
            travel_preferences = {
                "activity_interests": selected_activity_categories,
                "hotel_preference": hotel_price_level,
                "cuisine_regions": selected_cuisine_regions
            }

            preferences.update({
                "travel_preferences": travel_preferences,
                "activity_interests": selected_activity_categories,
                "hotel_preference": hotel_price_level,
                "cuisine_regions": selected_cuisine_regions
            })

            if "user_no" in st.session_state:
                print("Here")
                try:
                    from database.db_manager import DatabaseManager
                    db_manager = DatabaseManager()

                    preferences["timestamp"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    preferences["user_id"] = st.session_state.user_no
                    user_id = str(st.session_state.user_no)

                    result_file = db_manager.update_temp_with_preferences(user_id, preferences)

                    if result_file and os.path.exists(result_file):
                        st.success("✅ Your travel preferences have been saved successfully!")
                        try:
                            df = pd.read_csv(result_file)
                            if 'user_preferences' in df.columns:
                                user_prefs = json.loads(df['user_preferences'].iloc[0])
                                if 'travel_preferences' in user_prefs:
                                    st.sidebar.success("🗂️ Preferences verified in temp.csv")
                        except Exception as verify_err:
                            st.sidebar.error(f"❗ Verification error: {str(verify_err)}")

                except Exception as e:
                    st.error(f"⚠️ Error saving preferences: {str(e)}")
                    import traceback
                    st.sidebar.error(f"🪲 Error details: {traceback.format_exc()}")

        else:
            preferences.update({
                "activity_categories": st.session_state.activity_categories_selected,
                "hotel_price_level": st.session_state,
                "cuisine_regions": st.session_state.cuisine_regions_selected
            })

            activity_category_mapping = {
                "Cultural": ["museum", "art_gallery", "historical_landmark", "monument", "performing_arts_theater", "library", "cultural_center"],
                "Nature & Outdoors": ["park", "national_park", "state_park", "garden", "botanical_garden", "beach", "hiking_area", "trail_walking_path", "natural_feature", "mountain"],
                "Entertainment": ["amusement_park", "water_park", "movie_theater", "performing_arts_theater", "casino", "concert_hall"],
                "Shopping": ["shopping_mall", "market", "street_market", "department_store", "clothing_store", "specialty_food_shop", "gift_shop"],
                "Recreation": ["stadium", "sports_complex", "gym", "fitness_center", "swimming_pool", "golf_course", "spa"],
                "Nightlife": ["night_club", "bar", "pub", "lounge", "comedy_club"]
            }

            preferences["activity_api_types"] = [
                api for category in st.session_state.activity_categories_selected
                for api in activity_category_mapping.get(category, [])
            ]

            hotel_type_mapping = {
                "Budget": ["hostel", "motel", "campground", "guest_house", "lodge"],
                "Medium": ["hotel", "inn", "bed_and_breakfast", "resort"],
                "Luxury": ["hotel", "resort", "spa_resort", "luxury_hotel", "villa"]
            }

            preferences["hotel_types"] = hotel_type_mapping.get(st.session_state.hotel_price_level, ["hotel"])
            st.session_state.preferences = preferences
            if preferences and "travel_preferences" in preferences:
                user_id = st.session_state.user_no
                
                try:
                    # 导入数据库管理器
                    from database.db_manager import DatabaseManager
                    
                    # 创建数据库管理器实例
                    db_manager = DatabaseManager()
                    
                    # 修复现有temp.csv文件
                    fix_existing_temp_file(user_id)
                    
                    # 获取用户目录
                    user_dir = db_manager._get_user_dir(user_id)
                    temp_file_path = os.path.join(user_dir, "temp.csv")
                    
                    # 检查temp.csv是否存在
                    if os.path.exists(temp_file_path):
                        try:
                            # 读取现有的CSV文件
                            df = pd.read_csv(temp_file_path)
                            
                            # 检查是否有user_preferences列
                            if 'user_preferences' in df.columns:
                                # 解析现有的偏好数据
                                existing_prefs = json.loads(df['user_preferences'].iloc[0])
                                
                                # 添加或更新旅行偏好
                                existing_prefs["travel_preferences"] = preferences.get("travel_preferences")
                                
                                # 也直接添加单独的偏好字段，使其能够出现在CSV的单独列中
                                if "travel_preferences" in preferences and isinstance(preferences["travel_preferences"], dict):
                                    travel_prefs = preferences["travel_preferences"]
                                    if "activity_interests" in travel_prefs:
                                        existing_prefs["activity_interests"] = travel_prefs["activity_interests"]
                                    if "hotel_preference" in travel_prefs:
                                        existing_prefs["hotel_preference"] = travel_prefs["hotel_preference"]
                                    if "cuisine_regions" in travel_prefs:
                                        existing_prefs["cuisine_regions"] = travel_prefs["cuisine_regions"]
                                
                                # 更新到CSV文件
                                df['user_preferences'] = json.dumps(existing_prefs)
                                df.to_csv(temp_file_path, index=False)
                                
                                st.sidebar.success("✓ Updated travel preferences in existing flight data")
                                st.success("Your travel preferences have been saved with your flight selection!")
                            else:
                                st.sidebar.warning("No user_preferences column found in temp.csv")
                        except Exception as e:
                            st.sidebar.error(f"Error updating temp.csv: {str(e)}")
                    else:
                        st.sidebar.warning(f"temp.csv file not found at {temp_file_path}")
                except Exception as e:
                    st.sidebar.error(f"Error processing travel preferences: {str(e)}")
    if st.button("Generate Travel Plan", type="primary"):
        st.info("Generating your travel plan, this may take a few minutes...")
        if 'firstround' not in st.session_state:
            st.session_state.firstround = True
        st.switch_page("pages/chatbot.py")