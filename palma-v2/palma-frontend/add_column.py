
import sqlite3
import os

# Path to the database
db_path = os.path.join(os.getcwd(), 'instance', 'analyses.db')

if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    exit(1)

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if column exists
    cursor.execute("PRAGMA table_info(analysis)")
    columns = [info[1] for info in cursor.fetchall()]
    
    if 'confidence' not in columns:
        print("Adding 'confidence' column...")
        cursor.execute("ALTER TABLE analysis ADD COLUMN confidence FLOAT DEFAULT 0.0")
        conn.commit()
        print("Column added successfully.")
    else:
        print("'confidence' column already exists.")
        
    conn.close()
except Exception as e:
    print(f"Error: {e}")
