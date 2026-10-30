import streamlit as st
from database import init_db
from auth import render_auth_ui
from booking import render_booking_flow
from user_dashboard import render_user_dashboard
from admin import render_admin_panel

# Page Config
st.set_page_config(
    page_title="Cinema Seat Booking System",
    page_icon="🎬",
    layout="wide"
)

# Initialize Database on Startup
init_db()

def main():
    # Initialize Session State
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
    if "user" not in st.session_state:
        st.session_state["user"] = None

    # Sidebar Navigation
    st.sidebar.title("🍿 Cinema App")
    
    if not st.session_state["logged_in"]:
        render_auth_ui()
    else:
        user = st.session_state["user"]
        st.sidebar.markdown(f"Logged in as: **{user['username']}** ({user['role'].upper()})")
        
        # Navigation options based on role
        nav_options = ["🎬 Book Tickets", "👤 My Dashboard"]
        if user['role'] == 'admin':
            nav_options.append("🛠️ Admin Panel")
            
        choice = st.sidebar.radio("Navigation", nav_options)
        
        if st.sidebar.button("Log Out", use_container_width=True):
            st.session_state["logged_in"] = False
            st.session_state["user"] = None
            st.rerun()
            
        st.sidebar.markdown("---")
        
        # Render Selected View
        if choice == "🎬 Book Tickets":
            render_booking_flow()
        elif choice == "👤 My Dashboard":
            render_user_dashboard()
        elif choice == "🛠️ Admin Panel" and user['role'] == 'admin':
            render_admin_panel()

if __name__ == "__main__":
    main()