import streamlit as st
import pandas as pd
from database import get_connection

def add_show(movie_title: str, show_time: str, description: str) -> tuple[bool, str]:
    """Adds a new movie show to the database."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO shows (movie_title, show_time, description)
        VALUES (?, ?, ?)
        """, (movie_title.strip(), show_time.strip(), description.strip()))
        conn.commit()
        return True, "Show added successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error adding show: {e}"
    finally:
        conn.close()

def update_category_config(category_id: int, price: float, rows_count: int, seats_per_row: int) -> tuple[bool, str]:
    """Updates pricing and layout configuration for a seating category."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        UPDATE seat_pricing 
        SET price = ?, rows_count = ?, seats_per_row = ?
        WHERE id = ?
        """, (price, rows_count, seats_per_row, category_id))
        conn.commit()
        return True, "Category updated successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error updating category: {e}"
    finally:
        conn.close()

def add_category(category_name: str, price: float, rows_count: int, seats_per_row: int) -> tuple[bool, str]:
    """Adds a brand new seating section (e.g., Diamond, VIP)."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO seat_pricing (category, price, rows_count, seats_per_row)
        VALUES (?, ?, ?, ?)
        """, (category_name.strip(), price, rows_count, seats_per_row))
        conn.commit()
        return True, f"Section '{category_name}' added successfully!"
    except Exception as e:
        conn.rollback()
        return False, f"Error adding section (might already exist): {e}"
    finally:
        conn.close()

def render_admin_panel():
    """Renders the administrative control center."""
    st.subheader("🛠️ Admin Control Panel")
    
    tab1, tab2 = st.tabs(["🎬 Manage Shows", "💺 Seat Layout & Pricing"])
    
    # 1. MANAGE SHOWS
    with tab1:
        st.markdown("### Add New Movie Show")
        with st.form("add_show_form"):
            title = st.text_input("Movie Title")
            show_time = st.text_input("Show Time (YYYY-MM-DD HH:MM:SS)", value="2026-06-20 21:00:00")
            desc = st.text_area("Description")
            submit_show = st.form_submit_button("Add Show", use_container_width=True)
            
            if submit_show:
                if not title or not show_time:
                    st.error("Movie title and show time are required!")
                else:
                    success, msg = add_show(title, show_time, desc)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)
                        
        st.markdown("---")
        st.markdown("### Existing Shows")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shows ORDER BY show_time DESC")
        shows = cursor.fetchall()
        conn.close()
        
        if not shows:
            st.info("No shows found.")
        else:
            for s in shows:
                st.write(f"- **{s['movie_title']}** at `{s['show_time']}` — *{s['description']}*")

    # 2. SEAT LAYOUT & PRICING
    with tab2:
        st.markdown("### Configure Existing Seat Categories & Rows")
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM seat_pricing")
        categories = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        for cat in categories:
            with st.expander(f"🏷️ Category: {cat['category']} (Price: ₹{cat['price']}, Rows: {cat['rows_count']}, Seats/Row: {cat['seats_per_row']})"):
                with st.form(f"update_cat_{cat['id']}"):
                    new_price = st.number_input("Price (₹)", value=float(cat['price']), min_value=0.0, step=10.0)
                    new_rows = st.number_input("Number of Rows", value=int(cat['rows_count']), min_value=1, step=1)
                    new_seats = st.number_input("Seats Per Row", value=int(cat['seats_per_row']), min_value=1, step=1)
                    update_btn = st.form_submit_button("Update Configuration", use_container_width=True)
                    
                    if update_btn:
                        success, msg = update_category_config(cat['id'], new_price, new_rows, new_seats)
                        if success:
                            st.success(msg)
                            st.rerun()
                        else:
                            st.error(msg)
                            
        st.markdown("---")
        st.markdown("### Add New Section (e.g., Diamond, VIP Balcony)")
        with st.form("add_cat_form"):
            new_cat_name = st.text_input("Section Name")
            new_cat_price = st.number_input("Price (₹)", value=750.0, min_value=0.0, step=10.0)
            new_cat_rows = st.number_input("Number of Rows", value=1, min_value=1, step=1)
            new_cat_seats = st.number_input("Seats Per Row", value=8, min_value=1, step=1)
            add_cat_btn = st.form_submit_button("Add New Section", use_container_width=True)
            
            if add_cat_btn:
                if not new_cat_name:
                    st.error("Section name is required!")
                else:
                    success, msg = add_category(new_cat_name, new_cat_price, new_cat_rows, new_cat_seats)
                    if success:
                        st.success(msg)
                        st.rerun()
                    else:
                        st.error(msg)