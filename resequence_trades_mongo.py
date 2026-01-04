import os
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

def resequence_trades_mongo():
    """
    Re-sequences trade_no for each user to be 1, 2, 3... based on open_time.
    """
    print("🔄 Re-sequencing trades (MongoDB)...")
    
    # Connect using same env vars as app
    # Or hardcode default if env not set for script
    uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    db_name = os.getenv("DB_NAME", "JournalX")
    
    print(f"📡 Connecting to MongoDB at {uri}...")
    try:
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        print(f"✅ Connected to MongoDB!")
    except Exception as e:
        print(f"❌ Failed to connect to MongoDB: {e}")
        return

    db = client[db_name]
    
    # Get all distinct users
    users = db.trades.distinct("user_id")
    print(f"👥 Found {len(users)} users with trades.")
    
    total_updated = 0
    
    for user_id in users:
        print(f"\n👤 Processing user: {user_id}")
        
        # Get trades for user, sorted by time
        trades = list(db.trades.find({"user_id": user_id}).sort("open_time", 1))
        
        if not trades:
            continue
            
        print(f"   Found {len(trades)} trades.")
        
        # Update each trade with new sequence
        for index, trade in enumerate(trades):
            new_no = index + 1
            old_no = trade.get('trade_no')
            
            if old_no != new_no:
                db.trades.update_one(
                    {"_id": trade["_id"]},
                    {"$set": {"trade_no": new_no}}
                )
                print(f"   Trade {trade.get('symbol')} ({trade.get('open_time')}): #{old_no} -> #{new_no}")
                total_updated += 1
    
    print(f"\n✅ Resequencing complete. Updated {total_updated} trades.")
    client.close()

if __name__ == "__main__":
    resequence_trades_mongo()
