import sys
from sqlalchemy import create_engine, text, or_, and_
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import pandas as pd
from app.models.trade import Trade

# Database URL
SQLALCHEMY_DATABASE_URL = "sqlite:///./trading_journal.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def debug_weekly():
    db = SessionLocal()
    try:
        print("--- Debugging Weekly Review Logic ---")
        
        # 1. Get User ID (just grab the first user found in trades for now, or list all)
        # We'll just check all trades for all users to see what's happening
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        print(f"Date Range (for reference): {start_date} to {end_date}")

        # Fetch last 20 trades regardless of date to see what's going on
        trades = db.query(Trade).order_by(Trade.id.desc()).limit(20).all()
        
        if not trades:
            print("No trades found in database.")
            return

        print(f"Found {len(trades)} trades in specific user query (showing last 20).")
        
        data = []
        for t in trades:
            # Check if it WOULD pass the filter
            ref_time = t.close_time or t.open_time
            passes = False
            if ref_time:
                if ref_time >= start_date:
                    passes = True
            
            print(f"ID: {t.id} | User: {t.user_id} | Open: {t.open_time} | Close: {t.close_time} | P&L: {t.net_profit} | Passes Filter: {passes}")
            data.append({"net_profit": t.net_profit or 0})
            
        if data:
            df = pd.DataFrame(data)
            worst_val = df['net_profit'].min()
            print(f"Calculated Worst Trade Profit: {worst_val}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_weekly()
