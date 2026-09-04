import asyncio
from pymongo import MongoClient
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mongo_database import get_db

async def debug_trades():
    db = get_db()
    
    # Get all users with mt5 credentials
    creds = list(db.mt5_credentials.find({}))
    if not creds:
        print("No creds found.")
        return
        
    for cred in creds:
        user_id = cred.get("user_id")
        active_account = str(cred.get("account"))
        
        # Test the query
        query = {"user_id": user_id}
        if active_account:
            query["$or"] = [
                {"mt5_account": active_account},
                {"mt5_account": {"$exists": False}},
                {"mt5_account": None}
            ]
        
        trades = list(db.trades.find(query))
        print(f"User {user_id} - Active Account: {active_account}")
        print(f"Total trades with account matching: {len(trades)}")
        
        # Raw count
        all_trades = list(db.trades.find({"user_id": user_id}))
        print(f"Total raw trades for user: {len(all_trades)}")
        if len(all_trades) > 0:
            print(f"First trade mt5_account field: {all_trades[0].get('mt5_account')!r}")

if __name__ == "__main__":
    asyncio.run(debug_trades())
