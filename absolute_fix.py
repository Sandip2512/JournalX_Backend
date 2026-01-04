from app.mongo_database import get_db

def absolute_fix():
    db = get_db()
    # THE ONE FROM LOGS IS THE REAL ONE
    log_id = "e5a933cf-d99e-4b85-a2ff-379efbe82e0b"
    other_id = "e5a933ce-6330-466d-965c-60280eb4696c"
    
    # 1. Move ALL goals from the 'other' Sandip to the 'log' Sandip
    res_migrate = db.goals.update_many({"user_id": other_id}, {"$set": {"user_id": log_id}})
    print(f"Migrated {res_migrate.modified_count} goals from {other_id} to {log_id}")
    
    # 2. Ensure the goals for log_id have valid targets
    # We set them explicitly to be sure
    db.goals.update_one(
        {"user_id": log_id, "goal_type": "weekly"},
        {"$set": {"target_amount": 500.0, "is_active": True, "achieved": False}},
        upsert=True
    )
    db.goals.update_one(
        {"user_id": log_id, "goal_type": "monthly"},
        {"$set": {"target_amount": 2000.0, "is_active": True, "achieved": False}},
        upsert=True
    )
    
    # 3. Clean up any $0 targets for this user (force defaults)
    db.goals.update_many(
        {"user_id": log_id, "target_amount": {"$in": [0, 0.0, None]}},
        {"$set": {"target_amount": 500.0}} # Default to 500 if unknown
    )

    print("--- REMAINING GOALS FOR PRODUCTION USER ---")
    for g in db.goals.find({"user_id": log_id}):
         print(f"Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, Active: {g.get('is_active')}")

if __name__ == "__main__":
    absolute_fix()
