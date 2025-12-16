from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.trade import Trade
from app.models.user import User

def debug_trades():
    db: Session = SessionLocal()
    try:
        print("--- fetching users ---")
        users = db.query(User).all()
        for u in users:
            print(f"User: {u.email} (ID: {u.user_id})")
            
            print(f"--- Fetching trades for user {u.user_id} ---")
            trades = db.query(Trade).filter(Trade.user_id == u.user_id).all()
            print(f"Found {len(trades)} trades.")
            
            for t in trades[:10]: # Print first 10
                print(f"Trade {t.trade_no}: Net Profit={t.net_profit}, Open={t.open_time}, Close={t.close_time}")
                
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    debug_trades()
