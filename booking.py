import streamlit as st
import pandas as pd
from database import get_connection

def get_all_shows():
    """Fetches all upcoming shows."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM shows ORDER BY show_time ASC")
    shows = cursor.fetchall()
    conn.close()
    return [dict(show) for show in shows]

def get_seat_pricing():
    """Fetches category pricing and dimensions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seat_pricing")
    pricing = cursor.fetchall()
    conn.close()
    return {p['category']: dict(p) for p in pricing}

def ensure_seats_for_show(show_id: int):
    """Ensures seat records exist in the DB for a given show based on current pricing/layout config."""
    conn = get_connection()
    cursor = conn.cursor()
    
    pricing = get_seat_pricing()
    
    # Check if seats already exist for this show
    cursor.execute("SELECT COUNT(*) FROM seats WHERE show_id = ?", (show_id,))
    if cursor.fetchone()[0] > 0:
        conn.close()
        return

    # Generate seats based on configuration
    alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    row_counter = 0
    
    for category, config in pricing.items():
        rows_count = config['rows_count']
        seats_per_row = config['seats_per_row']
        
        for r in range(rows_count):
            if row_counter < len(alphabet):
                row_name = alphabet[row_counter]
            else:
                row_name = f"R{row_counter}"
            
            row_counter += 1
            
            for s_num in range(1, seats_per_row + 1):
                cursor.execute("""
                INSERT INTO seats (show_id, category, row_name, seat_number, status)
                VALUES (?, ?, ?, ?, 'available')
                """, (show_id, category, row_name, s_num))
                
    conn.commit()
    conn.close()

def get_show_seats(show_id: int):
    """Fetches all seats for a specific show."""
    ensure_seats_for_show(show_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM seats WHERE show_id = ? ORDER BY id", (show_id,))
    seats = cursor.fetchall()
    conn.close()
    return [dict(s) for s in seats]

def render_booking_flow():
    """Renders the show selection, interactive seat grid, and checkout flow."""
    st.subheader("🎬 Movie Booking & Seat Selection")
    
    shows = get_all_shows()
    if not shows:
        st.warning("No movie shows available at the moment. Check back later or ask an admin to add one.")
        return

    show_options = {f"{s['movie_title']} ({s['show_time']})": s['id'] for s in shows}
    selected_show_label = st.selectbox("Select a Movie Show", list(show_options.keys()))
    selected_show_id = show_options[selected_show_label]

    pricing = get_seat_pricing()
    
    # Display Legend
    st.markdown("---")
    cols_legend = st.columns(5)
    cols_legend[0].markdown("🟩 **Available**")
    cols_legend[1].markdown("🟥 **Booked**")
    cols_legend[2].markdown(f"🥈 **Silver**: ₹{pricing.get('Silver', {}).get('price', 150)}")
    cols_legend[3].markdown(f"🥇 **Gold**: ₹{pricing.get('Gold', {}).get('price', 300)}")
    cols_legend[4].markdown(f"💎 **Platinum/Diamond**: ₹{pricing.get('Platinum', {}).get('price', 500)}+")
    st.markdown("---")

    seats = get_show_seats(selected_show_id)
    
    # Group seats by category and row
    categories = list(pricing.keys())
    
    if "selected_seats" not in st.session_state:
        st.session_state["selected_seats"] = []

    st.write("### 💺 Select Your Seats")
    st.info("Click available seats below to select or unselect them.")

    selected_seat_ids = st.session_state["selected_seats"]

    for category in categories:
        cat_seats = [s for s in seats if s['category'] == category]
        if not cat_seats:
            continue
            
        st.markdown(f"#### 🏷️ {category} Section (₹{pricing[category]['price']} per seat)")
        
        # Group by row
        rows = sorted(list(set(s['row_name'] for s in cat_seats)))
        for row in rows:
            row_seats = sorted([s for s in cat_seats if s['row_name'] == row], key=lambda x: x['seat_number'])
            
            cols = st.columns(min(len(row_seats) + 1, 12))
            cols[0].write(f"**Row {row}**")
            
            for i, seat in enumerate(row_seats):
                col_idx = (i % 10) + 1
                if col_idx < len(cols):
                    seat_label = f"{row}{seat['seat_number']}"
                    is_booked = seat['status'] == 'booked'
                    is_selected = seat['id'] in selected_seat_ids
                    
                    if is_booked:
                        cols[col_idx].button(f"🚫 {seat_label}", disabled=True, key=f"seat_{seat['id']}")
                    else:
                        btn_label = f"✅ {seat_label}" if is_selected else f"💺 {seat_label}"
                        if cols[col_idx].button(btn_label, key=f"seat_{seat['id']}"):
                            if is_selected:
                                st.session_state["selected_seats"].remove(seat['id'])
                            else:
                                st.session_state["selected_seats"].append(seat['id'])
                            st.rerun()

    # Checkout Section
    if st.session_state["selected_seats"]:
        st.markdown("---")
        st.subheader("💳 Checkout Summary")
        
        # Calculate total
        conn = get_connection()
        cursor = conn.cursor()
        placeholders = ','.join(['?'] * len(st.session_state["selected_seats"]))
        cursor.execute(f"SELECT s.*, sp.price FROM seats s JOIN seat_pricing sp ON s.category = sp.category WHERE s.id IN ({placeholders})", st.session_state["selected_seats"])
        selected_details = [dict(row) for row in cursor.fetchall()]
        conn.close()

        total_amount = sum([item['price'] for item in selected_details])
        seat_names = [f"{item['category']} ({item['row_name']}{item['seat_number']})" for item in selected_details]

        st.write(f"**Selected Seats:** {', '.join(seat_names)}")
        st.write(f"**Total Amount to Pay:** ₹{total_amount:.2f}")

        with st.form("payment_form"):
            st.text_input("Cardholder Name", value=st.session_state["user"]["username"])
            st.text_input("Card Number", value="•••• •••• •••• 4242", type="password")
            pay_submit = st.form_submit_button(f"Confirm & Pay ₹{total_amount:.2f}", use_container_width=True)
            
            if pay_submit:
                user_id = st.session_state["user"]["id"]
                conn = get_connection()
                cursor = conn.cursor()
                
                try:
                    # Create booking record
                    cursor.execute("""
                    INSERT INTO bookings (user_id, show_id, total_amount, status)
                    VALUES (?, ?, ?, 'confirmed')
                    """, (user_id, selected_show_id, total_amount))
                    booking_id = cursor.lastrowid
                    
                    # Update seats status to 'booked' and record bridge table
                    for seat_id in st.session_state["selected_seats"]:
                        cursor.execute("UPDATE seats SET status = 'booked', booked_by = ? WHERE id = ?", (user_id, seat_id))
                        cursor.execute("INSERT INTO booking_seats (booking_id, seat_id) VALUES (?, ?)", (booking_id, seat_id))
                        
                    conn.commit()
                    st.success("🎉 Payment successful! Your seats have been booked.")
                    st.session_state["selected_seats"] = []
                    st.rerun()
                except Exception as e:
                    conn.rollback()
                    st.error(f"Booking failed due to an error: {e}")
                finally:
                    conn.close()