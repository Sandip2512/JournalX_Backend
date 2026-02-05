import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def detail_goals(user_id):
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "JournalX")
    client = MongoClient(uri)
    db = client[db_name]
    
    print(f"🎯 Detailed Goals for {user_id}:")
    goals = list(db.goals.find({"user_id": user_id}))
    if not goals:
        print("No goals found.")
        return
        
    for g in goals:
        print(f"- Type: {g.get('goal_type')} | Target: {g.get('target_amount')} | Active: {g.get('is_active')} | Achieved: {g.get('achieved')}")

if __name__ == "__main__":
    detail_goals("e5a933cf-d99e-4b85-a2ff-379efbe82e0b")
