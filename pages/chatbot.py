import streamlit as st
from api.llm_api import LLMApi  # Replace with your actual module
from config import load_api_keys
from utils import save_all_tempdata_to_memorybank
import pandas as pd
import os
import time

# 设置页面配置与标题
st.set_page_config(
    page_title="Travel Chatbot",
    page_icon="🤖",
    initial_sidebar_state='collapsed',
    layout="wide"
)
st.title("EECS 545 Travel Planner 🌏")

# 加载 API 密钥
load_api_keys()

# 初始化 LLM API 客户端
llm_api = LLMApi()

# Session state 初始化
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'latest_itinerary' not in st.session_state:
    st.session_state.latest_itinerary = None

if 'firstround' not in st.session_state:
    st.session_state.firstround = True

if 'preferences' not in st.session_state:
    st.session_state.preferences = None

if 'places_result' not in st.session_state:
    st.session_state.places_result = None

if 'user_query' not in st.session_state:
    st.session_state.user_query = None

if 'tempdata' not in st.session_state:
    st.session_state.tempdata = None

places_result = None
if st.session_state.preferences != None and st.session_state.user_query != None and st.session_state.places_result == None:
    try:
        import requests
        query_prompt = f"""The user is traveling to {st.session_state.user_query["destination"]} from {st.session_state.user_query["departure_date"]} to {st.session_state.user_query["return_date"]}."
        They will be traveling with {st.session_state.user_query["adults"]} adults and {st.session_state.user_query["children"]} children.
        Given the following user preferences, write a simple, concise sentence describing what types of places they might want to visit: {st.session_state.preferences}"
        """
        print(query_prompt)
        response = llm_api.generate_text(prompt=query_prompt, temperature=0.7, max_tokens=100)
        print(f"Here's LLM's response:\n{response}")
        query_text = response.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
        api_payload = {
                        "textQuery": query_text,
                        "languageCode": "en"
                    }
        headers = {
                        "Content-Type": "application/json",
                        "X-Goog-Api-Key": os.environ.get("GOOGLE_PLACES_API_KEY", ""),
                        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.types,places.rating,places.userRatingCount"
                    }
        r = requests.post("https://places.googleapis.com/v1/places:searchText", headers=headers, json=api_payload)
        if r.status_code == 200:
            places_result = r.json()
    except Exception as e:
        st.warning(f"Could not fetch Google Places: {str(e)}")
if places_result:
    st.session_state.place_result = places_result
    print(places_result)

user_dir = os.path.join('database', f'user_{st.session_state.user_no}')
os.makedirs(user_dir, exist_ok=True)

# 页面布局：左右分栏
left_col, right_col = st.columns([3, 2], gap="large")

# 左侧显示生成的行程结果
with left_col:
    st.markdown("### 📋 Generated Travel Itinerary")
    if st.session_state.latest_itinerary:
        st.markdown(st.session_state.latest_itinerary)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Itinerary"):
                destination = st.session_state.user_query.get('destination', 'itinerary')
                departure_date = st.session_state.user_query.get('departure_date', 'start')
                return_date = st.session_state.user_query.get('return_date', 'end')
                filename = f"{destination}_{departure_date}_to_{return_date}.md".replace(' ', '_')
                file_path = os.path.join(user_dir, filename)
            
                # Save the itinerary content to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(st.session_state.latest_itinerary)
                
                st.success(f"Itinerary saved successfully as {filename} in {user_dir}.")
                save_all_tempdata_to_memorybank(st.session_state.user_no)
        with col2:
            if st.button("🔄 Start Over"):
                # Reset relevant session state variables
                for key in ["latest_itinerary", "firstround", "user_query", "selected_flight", "places_result", "preferences"]:
                    if key in st.session_state:
                        del st.session_state[key]
                
                with st.spinner("Restarting..."):
                    time.sleep(1)
                st.switch_page("app.py")

# 右侧为聊天交互界面
with right_col:
    st.markdown("### 🤖 Travel Planner Chatbot")
    
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # 根据状态决定交互模式
    if st.session_state.firstround:
        # 第一轮：不显示输入框，直接根据 places_result 和 preferences 生成规划
        st.info("Generating initial itinerary based on recommended places...")
        full_prompt = f"""The user is traveling to {st.session_state.user_query["destination"]} from {st.session_state.user_query["departure_date"]} to {st.session_state.user_query["return_date"]}."
        They will be traveling with {st.session_state.user_query["adults"]} adults and {st.session_state.user_query["children"]} children."""

        if st.session_state.selected_flight:
            full_prompt += f"Here is the user's selected flight to their destination {st.session_state.selected_flight}, please include useful information in the itinerary.\n\n"

        if st.session_state.places_result:
            full_prompt += f"Here are the recommended places to visit:\n{st.session_state.places_result}\n\n"
            
        if st.session_state.preferences:
            full_prompt += f"Here are the preferences that the user selected:\n{st.session_state.preferences}\n\n"

        full_prompt += """Please generate a detailed travel itinerary in **Markdown format**, using the following structure and formatting:
---
# 🧳 Trip Itinerary: [Trip Title]

## Day X - [Theme or Highlight of the Day]  
📅 **Date:** YYYY-MM-DD  
**Estimated Cost:** *~XXX USD*
**Overview:** One-line summary of the day (e.g., "Explore historic Lisbon and enjoy local cuisine")
**Lodging:** 🏨 [Hotel/Hostel Name], [Location], 💰 *~XXX USD/night*


### 🗓 Schedule
- ⏰ **08:00** - [Breakfast at ...] *(~\\$10 USD)*
- 🏛 **10:00** - [Visit ...] *(~\\$15 entrance fee)*
- 🍽 **13:00** - [Lunch at ...] *(~\\$20)*
- 🚶 **15:00** - [Activity ...] *(free)*
- 🍷 **18:00** - [Dinner/Drinks at ...] *(~\\$25)*

### 💡 Suggestions
- [✓ Short travel tip, e.g., "Buy tickets in advance to skip lines"]
- [✓ Navigation help, e.g., "Use Tram 28 for a scenic route"]
- [✓ Food tip, e.g., "Try the grilled sardines at Mercado da Ribeira"]

---
Use:
- **Markdown format only**
- Clear headers
- Bullet points for tips
- Use emojis where appropriate

Do not include JSON or code blocks. Do not explain the itinerary. Just output it directly.\n"""

    else:
        # 后续轮次：显示用户输入框用于微调
        user_input = st.chat_input("Refine your travel plan:")
        if user_input:
            # 将用户输入加入聊天历史
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            # 构造 prompt，用用户输入加上上一次的行程作为参考
            full_prompt = f"{user_input}\n\n"
            if st.session_state.latest_itinerary:
                full_prompt += f"Previous itinerary:\n{st.session_state.latest_itinerary}\n\n"
            if st.session_state.preferences:
                full_prompt += f"Here are the preferences that the user selected:\n{st.session_state.preferences}\n\n"
            # 可选地追加 places_result 信息（如果需要）
            if st.session_state.places_result:
                full_prompt += f"Recommended places:\n{st.session_state.places_result}\n\n"
            full_prompt += """Please generate a refined detailed travel itinerary in **Markdown format** following the previous format, incorporating the above feedback. Prioritize user input.\n"""

    # 如果 full_prompt 不为空，则调用 LLM API 生成行程
    if 'full_prompt' in locals() and full_prompt:
        print("DEBUG: full_prompt content:")
        print(full_prompt)
        with st.spinner("Generating itinerary..."):
            response = llm_api.generate_text(prompt=full_prompt, temperature=0.6, max_tokens=3000)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        # 更新状态：首次生成后设置 firstround 为 False
        st.session_state.firstround = False
        if content:
            st.session_state.latest_itinerary = content
            st.session_state.chat_history.append({"role": "assistant", "content": "✅ Your itinerary has been generated and displayed in the left panel."})
        else:
            st.session_state.chat_history.append({"role": "assistant", "content": "⚠️ No itinerary was generated. Please try again."})
        st.rerun()

    if st.button("Reset", type="primary"):
            st.session_state.places_result = None
            st.session_state.firstround = True
            st.session_state.latest_itinerary = None
            st.session_state.chat_history = []
            st.rerun()
        