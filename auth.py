import sqlite3
import hashlib
import streamlit as st
from typing import Union
from database import get_connection

def hash_password(password: str) -> str:
    """Hashes a plain-text password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username: str, email: str, password: str) -> tuple[bool, str]:
    """Registers a new user in the database."""
    if not username or not email or not password:
        return False, "All fields are required!"
    
    hashed = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, 'user')",
            (username.strip(), email.strip().lower(), hashed)
        )
        conn.commit()
        return True, "Registration successful! You can now log in."
    except sqlite3.IntegrityError:
        return False, "Username or Email already exists."
    finally:
        conn.close()

def authenticate_user(username_or_email: str, password: str) -> tuple[bool, Union[dict, str]]:
    """Validates user credentials. Returns (True, user_dict) on success."""
    hashed = hash_password(password)
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, username, email, role 
        FROM users 
        WHERE (username = ? OR email = ?) AND password_hash = ?
    """, (username_or_email.strip(), username_or_email.strip().lower(), hashed))
    
    user = cursor.fetchone()
    conn.close()
    
    if user:
        return True, dict(user)
    return False, "Invalid username/email or password."

def update_password(user_id: int, current_pass: str, new_pass: str) -> tuple[bool, str]:
    """Updates password for an authenticated user."""
    conn = get_connection()
    cursor = conn.cursor()
    
    hashed_current = hash_password(current_pass)
    cursor.execute("SELECT id FROM users WHERE id = ? AND password_hash = ?", (user_id, hashed_current))
    
    if not cursor.fetchone():
        conn.close()
        return False, "Current password is incorrect."
    
    hashed_new = hash_password(new_pass)
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hashed_new, user_id))
    conn.commit()
    conn.close()
    return True, "Password updated successfully!"

def reset_password(email: str, new_pass: str) -> tuple[bool, str]:
    """Resets password using email verification."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id FROM users WHERE email = ?", (email.strip().lower(),))
    if not cursor.fetchone():
        conn.close()
        return False, "No account found with this email address."
    
    hashed_new = hash_password(new_pass)
    cursor.execute("UPDATE users SET password_hash = ? WHERE email = ?", (hashed_new, email.strip().lower()))
    conn.commit()
    conn.close()
    return True, "Password reset successful! Please log in with your new password."

def render_auth_ui():
    """Renders Login / Register / Forgot Password UI tabs in Streamlit."""
    st.subheader("Welcome to Cinema Seat Booking System")
    tab1, tab2, tab3 = st.tabs(["🔒 Login", "📝 Register", "🔑 Forgot Password"])

    with tab1:
        with st.form("login_form"):
            username_email = st.text_input("Username or Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Log In", use_container_width=True)
            
            if submit:
                success, result = authenticate_user(username_email, password)
                if success:
                    st.session_state["user"] = result
                    st.session_state["logged_in"] = True
                    st.success(f"Welcome back, {result['username']}!")
                    st.rerun()
                else:
                    st.error(result)

    with tab2:
        with st.form("register_form"):
            reg_username = st.text_input("Username")
            reg_email = st.text_input("Email")
            reg_password = st.text_input("Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            reg_submit = st.form_submit_button("Register", use_container_width=True)
            
            if reg_submit:
                if reg_password != confirm_password:
                    st.error("Passwords do not match!")
                else:
                    success, msg = register_user(reg_username, reg_email, reg_password)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)

    with tab3:
        with st.form("reset_pass_form"):
            reset_email = st.text_input("Enter Registered Email")
            new_pass = st.text_input("New Password", type="password")
            confirm_new = st.text_input("Confirm New Password", type="password")
            reset_submit = st.form_submit_button("Reset Password", use_container_width=True)
            
            if reset_submit:
                if new_pass != confirm_new:
                    st.error("Passwords do not match!")
                elif len(new_pass) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    success, msg = reset_password(reset_email, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)