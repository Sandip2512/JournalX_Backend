import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def check_user_data(user_id):
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "JournalX")
    
    print(f"📡 Connecting to Atlas...")
    
    try:
        client = MongoClient(uri)
        db = client[db_name]
        
        user = db.users.find_one({"user_id": user_id})
        if not user:
            print(f"❌ User {user_id} not found in 'users' collection.")
            # List all users to see if IDs are different
            all_users = list(db.users.find({}, {"user_id": 1, "email": 1}))
            print(f"👥 Available users ({len(all_users)}):")
            for u in all_users:
                print(f"  - {u.get('email')} | ID: {u.get('user_id')}")
        else:
            print(f"✅ User found: {user.get('email')} | Tier: {user.get('subscription_tier')}")
            
        trades_count = db.trades.count_documents({"user_id": user_id})
        print(f"📊 Trades for user: {trades_count}")
        
        goals_count = db.goals.count_documents({"user_id": user_id})
        print(f"🎯 Goals for user: {goals_count}")
        
        mt5_creds = db.mt5_credentials.find_one({"user_id": user_id})
        print(f"🔌 MT5 Linked: {'Yes' if mt5_creds else 'No'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    # From logs: e5a933cf-d99e-4b85-a2ff-379efbe82e0b
    # Let's check for any user if id is none
    check_user_data("e5a933cf-d99e-4b85-a2ff-379efbe82e0b")
