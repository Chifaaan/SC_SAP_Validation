import streamlit as st

pages = {
    "Main Menus":
    [
        st.Page("pages/login.py"),
        st.Page("pages/home.py", title="Home", icon=":material/home:"),
        st.Page("pages/process.py", title="Process")
    ],

    "Validation":
    [
        st.Page("pages/retur.py", title="Retur File", icon=":material/bar_chart_4_bars:"),
        st.Page("pages/dashboard.py", title="Dashboard", icon=":material/dashboard:")
    ],
    # "Chatbot":
    # [
    #     st.Page("pages/chatbot.py", title="Chatbot", icon=":material/smart_toy:")
    # ]
}



pg = st.navigation(pages, position="hidden")
pg.run()
