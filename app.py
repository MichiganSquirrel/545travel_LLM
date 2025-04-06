import streamlit as st
import time

if "user_no" not in st.session_state:
    st.session_state.user_no = None

# def logout():
#     st.session_state.user_no = None
#     st.rerun()

st.title("EECS 545 Travel Planner 🌏")
st.logo("images/TravelPlanner_Logo.png", icon_image="images/TravelPlanner_Logo.png")
user_no = st.session_state.user_no

st.markdown("## 🔐 Welcome to the Log In Page")
st.markdown("Please enter your user number to continue.")
user_no = st.number_input("👤 User Number", min_value=0, step=1, key="input_user_no")
if st.button("Log In", type="primary"):
    st.session_state.user_no = user_no
    st.success(f"Logged in as User #{user_no}")
    with st.spinner("Redirecting you to flight search page"):
        time.sleep(1)
    st.switch_page("pages/flightquery.py")