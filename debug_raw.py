import sqlite3
from datetime import datetime
import pandas as pd

# Database path (assuming standard location relative to backend)
DB_PATH = "trading_journal.db"

def debug_raw():
    try:
        print("--- Debugging Raw SQL ---")
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Get table schema to verify columns
        # cursor.execute("PRAGMA table_info(trades)")
        # columns = cursor.fetchall()
        # print("Columns:", [c[1] for c in columns])
        
        # Fetch last 20 trades
        print("\n--- Last 20 Trades ---")
        cursor.execute("SELECT id, user_id, net_profit, open_time, close_time FROM trades ORDER BY id DESC LIMIT 20")
        rows = cursor.fetchall()
        
        if not rows:
            print("No trades found.")
        
        for row in rows:
            # ID, User, Profit, Open, Close
            print(f"ID: {row[0]} | User: {row[1]} | Profit: {row[2]} | Open: {row[3]} | Close: {row[4]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    debug_raw()
