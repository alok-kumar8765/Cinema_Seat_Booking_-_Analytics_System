import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_connection
from auth import update_password

def cancel_booking(booking_id: int):
    """Cancels a booking, frees up seats, and updates booking status."""
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Get seats associated with this booking
        cursor.execute("SELECT seat_id FROM booking_seats WHERE booking_id = ?", (booking_id,))
        seat_rows = cursor.fetchall()
        seat_ids = [row['seat_id'] for row in seat_rows]
        
        # Free up the seats
        if seat_ids:
            placeholders = ','.join(['?'] * len(seat_ids))
            cursor.execute(f"UPDATE seats SET status = 'available', booked_by = NULL WHERE id IN ({placeholders})", seat_ids)
            
        # Update booking status
        cursor.execute("UPDATE bookings SET status = 'cancelled' WHERE id = ?", (booking_id,))
        conn.commit()
        return True, "Booking successfully cancelled and seats released."
    except Exception as e:
        conn.rollback()
        return False, f"Failed to cancel booking: {e}"
    finally:
        conn.close()

def render_user_dashboard():
    """Renders user profile settings, bookings management, and expense analytics."""
    user = st.session_state["user"]
    st.subheader(f"👤 User Dashboard: {user['username']}")
    
    tab1, tab2, tab3 = st.tabs(["🎟️ My Bookings", "📊 Expense Analytics", "⚙️ Account Settings"])

    # 1. MY BOOKINGS TAB
    with tab1:
        st.markdown("### Your Ticket Bookings")
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT b.id as booking_id, sh.movie_title, sh.show_time, b.total_amount, b.booking_date, b.status
            FROM bookings b
            JOIN shows sh ON b.show_id = sh.id
            WHERE b.user_id = ?
            ORDER BY b.booking_date DESC
        """, (user['id'],))
        bookings = [dict(row) for row in cursor.fetchall()]
        
        if not bookings:
            st.info("You haven't made any bookings yet.")
        else:
            for b in bookings:
                # Fetch seat details for this booking
                cursor.execute("""
                    SELECT s.category, s.row_name, s.seat_number 
                    FROM booking_seats bs 
                    JOIN seats s ON bs.seat_id = s.id 
                    WHERE bs.booking_id = ?
                """, (b['booking_id'],))
                seats = cursor.fetchall()
                seat_str = ", ".join([f"{s['category']} ({s['row_name']}{s['seat_number']})" for s in seats])
                
                with st.expander(f"🎬 {b['movie_title']} — ₹{b['total_amount']} ({b['status'].upper()})"):
                    st.write(f"**Show Time:** {b['show_time']}")
                    st.write(f"**Booked On:** {b['booking_date']}")
                    st.write(f"**Seats:** {seat_str}")
                    st.write(f"**Status:** {b['status']}")
                    
                    if b['status'] == 'confirmed':
                        if st.button(f"Cancel Booking #{b['booking_id']}", key=f"cancel_{b['booking_id']}"):
                            success, msg = cancel_booking(b['booking_id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
        conn.close()

    # 2. EXPENSE ANALYTICS TAB
    with tab2:
        st.markdown("### 📈 Spending Analytics")
        conn = get_connection()
        query = """
            SELECT b.booking_date, b.total_amount
            FROM bookings b
            WHERE b.user_id = ? AND b.status = 'confirmed'
        """
        df = pd.read_sql(query, conn, params=(user['id'],))
        conn.close()
        
        if df.empty:
            st.info("No expense data available yet. Book some shows to see your analytics!")
        else:
            df['booking_date'] = pd.to_datetime(df['booking_date'])
            df['Year'] = df['booking_date'].dt.year
            df['Month'] = df['booking_date'].dt.strftime('%Y-%m')
            
            # Monthly Expenses Bar Chart
            monthly_df = df.groupby('Month')['total_amount'].sum().reset_index()
            fig_monthly = px.bar(
                monthly_df, x='Month', y='total_amount',
                title="Monthly Cinema Expenses",
                labels={'total_amount': 'Total Spent (₹)', 'Month': 'Month'},
                color_discrete_sequence=['#636EFA']
            )
            st.plotly_chart(fig_monthly, use_container_width=True)
            
            # Yearly Expenses Line Chart
            yearly_df = df.groupby('Year')['total_amount'].sum().reset_index()
            fig_yearly = px.line(
                yearly_df, x='Year', y='total_amount', markers=True,
                title="Yearly Cinema Expenses",
                labels={'total_amount': 'Total Spent (₹)', 'Year': 'Year'},
                color_discrete_sequence=['#00CC96']
            )
            st.plotly_chart(fig_yearly, use_container_width=True)

    # 3. ACCOUNT SETTINGS TAB
    with tab3:
        st.markdown("### 🔐 Security & Password Update")
        with st.form("update_pass_form"):
            current_pass = st.text_input("Current Password", type="password")
            new_pass = st.text_input("New Password", type="password")
            confirm_pass = st.text_input("Confirm New Password", type="password")
            update_submit = st.form_submit_button("Update Password", use_container_width=True)
            
            if update_submit:
                if new_pass != confirm_pass:
                    st.error("New passwords do not match!")
                elif len(new_pass) < 4:
                    st.error("Password must be at least 4 characters long.")
                else:
                    success, msg = update_password(user['id'], current_pass, new_pass)
                    if success:
                        st.success(msg)
                    else:
                        st.error(msg)