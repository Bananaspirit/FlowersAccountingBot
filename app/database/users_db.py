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
        role TEXT DEFAULT NULL,
        name TEXT
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

def add_unknown_user_if_not_exists(user_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO users (user_id, name) VALUES (?, ?)", (user_id, name))
    conn.commit()
    conn.close()

def user_exists(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return True
    return False

def update_user_role(user_id, role):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()

def create_first_admin(user_id, name):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO users (user_id, role, name) VALUES (?, ?, ?)", (user_id, "admin", name))
    conn.commit()
    conn.close()

def get_user_role(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT role FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0]

def get_list_of_admins(role):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users WHERE role=?", (role,))
    users_ids = cursor.fetchone()
    cursor.execute("SELECT name FROM users WHERE role=?", (role,))
    users_names = cursor.fetchone()
    conn.close()
    
    result = dict()
    for i in range(len(users_ids)):
        result[users_ids[i]] = users_names[i]

    if result:
        return result
    return None

def set_user_role(user_id, role):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("REPLACE INTO users (user_id, role) VALUES (?, ?)", (user_id, role))
    conn.commit()
    conn.close()

def get_all_users_by_role(role):
    """Retrieve all users from the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, name FROM users WHERE role=?", (role,))
    users = cursor.fetchall()
    conn.close()
    return users

def delete_user(user_id, role):
    """Delete a user by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET role = ? WHERE user_id = ?", (role, user_id))
    conn.commit()
    conn.close()

# get_list_of_admins("admin")
# is_table_empty("users")
# get_user_role(991874174)