import streamlit as st
from api.llm_api import LLMApi  # Replace with your actual module
from config import load_api_keys



# Divider and section title

st.set_page_config(
        page_title="Travel Chatbot",
        page_icon="🤖",
        initial_sidebar_state='collapsed',

    )
st.title("EECS 545 Travel Planner 🌏")
st.logo("images/TravelPlanner_Logo.png", icon_image="images/TravelPlanner_Logo.png")

# Load API keys
load_api_keys()

# Initialize LLM API
llm_api = LLMApi()

# Session state setup
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

if 'latest_itinerary' not in st.session_state:
    st.session_state.latest_itinerary = None

# Layout with columns
left_col, right_col = st.columns([3, 2], gap="large")
if 'firstround' not in st.session_state:
    st.session_state.firstround = True

# Left panel: Display the latest itinerary
with left_col:
    st.markdown("### 📋 Generated Travel Itinerary (Markdown)")
    if st.session_state.latest_itinerary:
        st.markdown(st.session_state.latest_itinerary)
    else:
        st.markdown("Your generated itinerary will appear here.")

# Right panel: Chat interface
with right_col:
    
    st.markdown("### 🤖 Travel Planner Chatbot")

    # Display chat history
    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
    #print(st.session_state.tempdata)
    #print(st.session_state.firstround)
    # User input
    if ('tempdata' not in st.session_state) or (st.session_state.firstround==False):
        user_input = st.chat_input("Describe your trip here!")
    else:
        user_input = "Please generate a detailed travel plan with regard to my flight destination\n"

    if user_input:
        # Append user message to chat history
        st.session_state.chat_history.append({"role": "user", "content": user_input})

        # Construct prompt for LLM
        full_prompt = f"{user_input}\n\n"

        full_prompt += """Please generate a detailed travel itinerary in **Markdown format**, using the following structure and formatting:

---

# 🧳 Trip Itinerary: [Trip Title]

## Day X - [Theme or Highlight of the Day]
**Estimated Cost:** ~$XXX USD  
**Overview:** One-line summary of the day (e.g., "Explore historic Lisbon and enjoy local cuisine")

### 🗓 Schedule
- ⏰ **08:00** - [Breakfast at ...] *(~$10 USD)*
- 🏛 **10:00** - [Visit ...] *(~$15 entrance fee)*
- 🍽 **13:00** - [Lunch at ...] *(~$20)*
- 🚶 **15:00** - [Activity ...] *(free)*
- 🍷 **18:00** - [Dinner/Drinks at ...] *(~$25)*

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

        if st.session_state.latest_itinerary:
            full_prompt += f"Previous itinerary:\n{st.session_state.latest_itinerary}\n\n"
        if 'tempdata' not in st.session_state:
            st.session_state.tempdata = None
        if st.session_state.tempdata:
            full_prompt += f"Here is the flight that the user selected, mention the last flight segment in the itinerary:\n{st.session_state.tempdata}\n\n"
        if 'preferences' not in st.session_state:
            st.session_state.preferences = None
        if st.session_state.preferences:
            full_prompt += f"Here are the preferences that the user selected:\n{st.session_state.preferences}\n\n"
        print(full_prompt)

        # Display spinner while generating response
        with st.spinner("Generating itinerary..."):
            # Generate itinerary using LLM API
            response = llm_api.generate_text(prompt=full_prompt, temperature=0.6, max_tokens=3000)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        st.session_state.firstround = False
        if content:
            # Update the latest itinerary in session state
            st.session_state.latest_itinerary = content
            # Append confirmation message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": "✅ Your itinerary has been generated and displayed in the left panel."})
        else:
            # Append error message to chat history
            st.session_state.chat_history.append({"role": "assistant", "content": "⚠️ No itinerary was generated. Please try again."})
        st.rerun()