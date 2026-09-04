import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Database URL (assuming valid from app.database or hardcoded for debug)
SQLALCHEMY_DATABASE_URL = "sqlite:///./trading_journal.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def debug_trades():
    db = SessionLocal()
    try:
        print("--- Inspecting Trades ---")
        # Use raw SQL to avoid model definition issues
        result = db.execute(text("SELECT id, user_id, net_profit, open_time, close_time FROM trades ORDER BY id DESC LIMIT 20"))
        rows = result.fetchall()
        
        if not rows:
            print("No trades found in database.")
            return

        for row in rows:
            print(f"ID: {row[0]}, User: {row[1]}, Profit: {row[2]}, Open: {row[3]}, Close: {row[4]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_trades()
