import asyncio
from pymongo import MongoClient
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.mongo_database import get_db

async def migrate_trades_accounts():
    db = get_db()
    
    # Get all users with mt5 credentials
    creds_cursor = db.mt5_credentials.find({})
    updated = 0
    total = 0
    for cred in creds_cursor:
        user_id = cred.get("user_id")
        account_id = cred.get("account")
        if not user_id or not account_id:
            continue
            
        str_account = str(account_id)
        
        # Tag all their untagged trades with this account (since they were fetched previously on this account)
        result = db.trades.update_many(
            {"user_id": user_id, "mt5_account": {"$exists": False}}, 
            {"$set": {"mt5_account": str_account}}
        )
        updated += result.modified_count
        
    print(f"Migration completed. Updated {updated} existing trades with mt5_account.")

if __name__ == "__main__":
    asyncio.run(migrate_trades_accounts())
