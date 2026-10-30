import sqlite3
import hashlib

DB_NAME = "cinema_app.db"

def get_connection():
    """Returns a connection to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row  # Allows dictionary-like access to rows
    return conn

def init_db():
    """Initializes the database schema and creates default admin if not exists."""
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT DEFAULT 'user'
    )
    """)

    # 2. Shows Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS shows (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        movie_title TEXT NOT NULL,
        show_time TEXT NOT NULL,
        description TEXT
    )
    """)

    # 3. Seat Pricing & Layout Configuration Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seat_pricing (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT UNIQUE NOT NULL,  -- Silver, Gold, Platinum, Diamond
        price REAL NOT NULL,
        rows_count INTEGER NOT NULL,
        seats_per_row INTEGER NOT NULL
    )
    """)

    # 4. Seats Table (Tracks individual seat states per show)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        show_id INTEGER,
        category TEXT NOT NULL,
        row_name TEXT NOT NULL,
        seat_number INTEGER NOT NULL,
        status TEXT DEFAULT 'available', -- 'available' or 'booked'
        booked_by INTEGER,
        FOREIGN KEY (show_id) REFERENCES shows(id),
        FOREIGN KEY (booked_by) REFERENCES users(id)
    )
    """)

    # 5. Bookings / Transactions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        show_id INTEGER,
        total_amount REAL NOT NULL,
        booking_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'confirmed', -- 'confirmed' or 'cancelled'
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (show_id) REFERENCES shows(id)
    )
    """)

    # 6. Booking-Seats Bridge Table (Supports multi-seat bookings)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS booking_seats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        booking_id INTEGER,
        seat_id INTEGER,
        FOREIGN KEY (booking_id) REFERENCES bookings(id),
        FOREIGN KEY (seat_id) REFERENCES seats(id)
    )
    """)

    # Insert default pricing if table is empty
    cursor.execute("SELECT COUNT(*) FROM seat_pricing")
    if cursor.fetchone()[0] == 0:
        default_categories = [
            ('Silver', 150.0, 3, 10),     # 3 rows, 10 seats per row
            ('Gold', 300.0, 3, 10),
            ('Platinum', 500.0, 2, 10),
            ('Diamond', 800.0, 1, 8)
        ]
        cursor.executemany("""
        INSERT INTO seat_pricing (category, price, rows_count, seats_per_row) 
        VALUES (?, ?, ?, ?)
        """, default_categories)

    # Insert a default admin user if none exists (Username: admin, Password: password123)
    cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'admin'")
    if cursor.fetchone()[0] == 0:
        admin_pass = hashlib.sha256("password123".encode()).hexdigest()
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """, ('admin', 'admin@cinema.com', admin_pass, 'admin'))

    # Insert a sample show if none exists
    cursor.execute("SELECT COUNT(*) FROM shows")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
        INSERT INTO shows (movie_title, show_time, description)
        VALUES (?, ?, ?)
        """, ('Interstellar (Sci-Fi Epic)', '2026-06-15 19:30:00', 'A team of explorers travel through a wormhole in space.'))

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully!")