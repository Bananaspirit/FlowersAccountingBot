import sqlite3
from config import DB_PATH

# DB_PATH = "app/database/bot_users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create users table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        role TEXT
    )
    ''')
    
    conn.commit()
    conn.close()

def is_table_empty(table_name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
    result = cursor.fetchone()

    conn.close()

    return result[0] == 0

def create_admin(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, "admin"))
    conn.commit()
    conn.close()

def get_user_role(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0]
    return None  # Default role if not found

def get_list_of_admins(role):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE role=?", (role,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result
    return None

def set_user_role(user_id, role):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
    conn.commit()
    conn.close()

# get_list_of_admins("admin")