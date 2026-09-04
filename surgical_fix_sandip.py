from app.mongo_database import get_db

def fix_sandip_production():
    db = get_db()
    user_id = "e5a933ce-6330-466d-965c-60280eb4696c" # The correct Sandip UUID
    
    # 1. Clean up broken goals (those with target_amount as None or missing)
    db.goals.update_many(
        {"user_id": user_id, "target_amount": None},
        {"$set": {"target_amount": 0.0}}
    )
    
    # 2. Specifically set valid targets if they are $0
    # Let's set some defaults matching his previous intentions if possible, 
    # or just ensure they aren't $0 so they show up.
    
    # Weekly Target: $500
    db.goals.update_one(
        {"user_id": user_id, "goal_type": "weekly", "is_active": True},
        {"$set": {"target_amount": 500.0}},
        upsert=True
    )
    
    # Monthly Target: $2000
    db.goals.update_one(
        {"user_id": user_id, "goal_type": "monthly", "is_active": True},
        {"$set": {"target_amount": 2000.0}},
        upsert=True
    )
    
    print("Sandip's Production Goals have been surgically repaired and targets set.")

if __name__ == "__main__":
    fix_sandip_production()
