import sqlite3
from contextlib import contextmanager
from werkzeug.security import generate_password_hash, check_password_hash

DB_PATH = "meditrust.db"


@contextmanager
def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'patient',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'patient'")
        except sqlite3.OperationalError:
            pass  # column already exists, safe to ignore
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS food_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                ordered_by TEXT NOT NULL,
                room_number TEXT NOT NULL,
                items TEXT NOT NULL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                doctor_name TEXT NOT NULL,
                department TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS medications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                medicine_name TEXT NOT NULL,
                dosage TEXT,
                timings TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT NOT NULL DEFAULT 'unpaid',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sos_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                room_number TEXT NOT NULL,
                message TEXT,
                status TEXT NOT NULL DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS discharge_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                patient_name TEXT NOT NULL,
                diagnosis TEXT,
                admission_date TEXT,
                discharge_date TEXT,
                doctor_notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)


def create_user(username: str, email: str, password: str, role: str = "patient") -> bool:
    try:
        with get_connection() as conn:
            conn.execute(
                "INSERT INTO users (username, email, password_hash, role) VALUES (?, ?, ?, ?)",
                (username, email, generate_password_hash(password), role),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def verify_user(username: str, password: str):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()
        if row and check_password_hash(row["password_hash"], password):
            return dict(row)
    return None


def get_user_by_id(user_id: int):
    with get_connection() as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
        return dict(row) if row else None


def log_chat(user_id, question: str, answer: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO chat_history (user_id, question, answer) VALUES (?, ?, ?)",
            (user_id, question, answer),
        )


def get_chat_history(user_id, limit: int = 20):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT question, answer, created_at FROM chat_history "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_users():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, username, email, role, created_at FROM users ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_chat_history(limit: int = 100):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT chat_history.id, users.username, question, answer, chat_history.created_at "
            "FROM chat_history JOIN users ON users.id = chat_history.user_id "
            "ORDER BY chat_history.created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]


def log_food_order(user_id, ordered_by: str, room_number: str, items: str, notes: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO food_orders (user_id, ordered_by, room_number, items, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, ordered_by, room_number, items, notes),
        )


def get_user_food_orders(user_id, limit: int = 10):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT ordered_by, room_number, items, notes, created_at FROM food_orders "
            "WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit),
        ).fetchall()
        return [dict(r) for r in rows]

# ===================== Appointments =====================

def book_appointment(user_id, doctor_name: str, department: str, appointment_date: str, appointment_time: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO appointments (user_id, doctor_name, department, appointment_date, appointment_time) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, doctor_name, department, appointment_date, appointment_time),
        )


def get_user_appointments(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, doctor_name, department, appointment_date, appointment_time, status, created_at "
            "FROM appointments WHERE user_id = ? ORDER BY appointment_date DESC, appointment_time DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def cancel_appointment(appointment_id, user_id):
    with get_connection() as conn:
        conn.execute(
            "UPDATE appointments SET status = 'cancelled' WHERE id = ? AND user_id = ?",
            (appointment_id, user_id),
        )


# ===================== Medications =====================

def add_medication(user_id, medicine_name: str, dosage: str, timings: str, notes: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO medications (user_id, medicine_name, dosage, timings, notes) "
            "VALUES (?, ?, ?, ?, ?)",
            (user_id, medicine_name, dosage, timings, notes),
        )


def get_user_medications(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, medicine_name, dosage, timings, notes, created_at "
            "FROM medications WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def delete_medication(medication_id, user_id):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM medications WHERE id = ? AND user_id = ?",
            (medication_id, user_id),
        )


# ===================== Bills =====================

def add_bill(user_id, description: str, amount: float, status: str = "unpaid"):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO bills (user_id, description, amount, status) VALUES (?, ?, ?, ?)",
            (user_id, description, amount, status),
        )


def get_user_bills(user_id):
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, description, amount, status, created_at FROM bills "
            "WHERE user_id = ? ORDER BY created_at DESC",
            (user_id,),
        ).fetchall()
        return [dict(r) for r in rows]


# ===================== SOS Alerts =====================

def log_sos(user_id, room_number: str, message: str = ""):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sos_alerts (user_id, room_number, message) VALUES (?, ?, ?)",
            (user_id, room_number, message),
        )


def get_active_sos_alerts():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT sos_alerts.id, users.username, sos_alerts.room_number, "
            "sos_alerts.message, sos_alerts.created_at "
            "FROM sos_alerts JOIN users ON users.id = sos_alerts.user_id "
            "WHERE sos_alerts.status = 'active' ORDER BY sos_alerts.created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def resolve_sos(alert_id):
    with get_connection() as conn:
        conn.execute("UPDATE sos_alerts SET status = 'resolved' WHERE id = ?", (alert_id,))


# ===================== Discharge Summaries =====================

def save_discharge_summary(user_id, patient_name, diagnosis, admission_date, discharge_date, doctor_notes):
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO discharge_summaries "
            "(user_id, patient_name, diagnosis, admission_date, discharge_date, doctor_notes) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (user_id, patient_name, diagnosis, admission_date, discharge_date, doctor_notes),
        )
        return cur.lastrowid


def get_discharge_summary(summary_id, user_id):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM discharge_summaries WHERE id = ? AND user_id = ?",
            (summary_id, user_id),
        ).fetchone()
        return dict(row) if row else None
