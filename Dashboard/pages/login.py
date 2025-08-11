import streamlit as st
import requests
from streamlit.errors import StreamlitAPIException

def login_user(username, password):
    """
    Sends credentials to the n8n backend API and returns the response.
    """
    # IMPORTANT: Replace this with your actual n8n webhook URL
    api_url = "http://localhost:5678/webhook/login"
    
    payload = {
        "username": username,
        "password": password
    }
    
    try:
        response = requests.post(api_url, json=payload, timeout=5)
        response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Failed to connect to the login service: {e}")
        return None

# --- Streamlit Page Configuration ---
st.set_page_config(page_title="KFA Portal Login", layout="centered", initial_sidebar_state="collapsed")

# --- Initialize Session State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.role = None

# --- Main Login Logic ---
st.title("Company Portal Login")
st.write("Please enter your credentials to access the portal.")

# If user is already logged in, show a message and a link to the main app
if st.session_state.logged_in:
    st.success(f"You are already logged in as **{st.session_state.role}**.")
    st.page_link("pages/retur.py", label="Go to App", icon="🚀")
    st.stop()

# --- Login Form ---
with st.form("login_form"):
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login", type="secondary")

# --- Login Creds ---
col1, col2 = st.columns(2)
with col1:
    st.subheader("Role Supply Chain")
    st.warning("Username: `sc_user`")
    st.warning("Password: `user123`")
with col2:
    st.subheader("Role Accountant")
    st.warning("Username: `acc_user`")
    st.warning("Password: `user123`")

if submitted:
    if not username or not password:
        st.warning("Please enter both username and password.")
    else:
        with st.spinner("Authenticating..."):
            api_response = login_user(username, password)
            
            if api_response:
                message = api_response.get("message")
                role = api_response.get("role")
                user = api_response.get("user")
                
                if message == "Login Success" and role:
                    # On successful login, save state and switch page
                    st.session_state.logged_in = True
                    st.session_state.role = role
                    st.session_state.user = user
                    try:
                        st.switch_page("pages/process.py")
                    except StreamlitAPIException:
                         # Handle cases where st.switch_page might not be available in older versions
                         st.info("Please navigate to the 'retur' page from the sidebar.")

                else:
                    # Show error message from API if login fails
                    st.error(message or "Invalid username or password.")

        
