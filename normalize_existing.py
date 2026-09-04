import asyncio
from pymongo import MongoClient
import os
import sys

# Add app to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.mt5_service import normalize_symbol
from app.mongo_database import get_db

async def migrate_trades():
    db = get_db()
    
    trades = db.trades.find({})
    updated = 0
    total = 0
    for trade in trades:
        total += 1
        old_sym = trade.get('symbol', '')
        if old_sym:
            new_sym = normalize_symbol(old_sym)
            if new_sym and new_sym != old_sym:
                db.trades.update_one({'_id': trade['_id']}, {'$set': {'symbol': new_sym}})
                print(f"Updated {old_sym} -> {new_sym}")
                updated += 1
                
    print(f"Completed mapping. Total evaluated: {total}, Normalized: {updated}")

if __name__ == "__main__":
    asyncio.run(migrate_trades())
