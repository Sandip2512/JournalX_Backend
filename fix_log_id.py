from app.mongo_database import get_db

def log_id_fix():
    db = get_db()
    # THE ID FROM RAILWAY LOGS:
    log_id = "e5a933cf-d99e-4b85-a2ff-379efbe82e0b"
    
    user = db.users.find_one({"user_id": log_id})
    if user:
        print(f"Found user from logs: {user.get('first_name')} ({log_id})")
    else:
        print(f"User for log_id {log_id} NOT FOUND in production users collection.")
        # Check by first_name again to see all IDs
        sandips = list(db.users.find({"first_name": "Sandip"}))
        for s in sandips:
             print(f"Found Sandip: UUID={s.get('user_id')}, Email={s.get('email')}")

    # Check goals for the specific ID from logs
    goals = list(db.goals.find({"user_id": log_id}))
    print(f"\nGoals found for {log_id}: {len(goals)}")
    for g in goals:
        print(f" - {g.get('goal_type')}: Target={g.get('target_amount')}, Active={g.get('is_active')}, G_ID={g.get('_id')}")

    # Broad fix: Any goal with target_amount 0.0 or None should be set to a default to ensure visibility
    # This acts as a catch-all safety net.
    
    # Actually, let's just surgically fix THIS ID from logs
    if not goals or any(g.get('target_amount') in [0, 0.0, None] for g in goals):
        print("\nSurgically fixing goals for log_id...")
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
        print("Done.")

if __name__ == "__main__":
    log_id_fix()
