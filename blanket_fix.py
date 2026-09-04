from app.mongo_database import get_db

def blanket_fix():
    db = get_db()
    
    # 1. Get ALL Sandip IDs
    sandips = list(db.users.find({"first_name": "Sandip"}))
    sandip_ids = [s.get("user_id") for s in sandips]
    print(f"Fixing for all Sandips: {sandip_ids}")
    
    for uid in sandip_ids:
        # WEEKLY
        db.goals.update_one(
            {"user_id": uid, "goal_type": "weekly"},
            {"$set": {"target_amount": 500.0, "is_active": True, "achieved": False}},
            upsert=True
        )
        # MONTHLY
        db.goals.update_one(
            {"user_id": uid, "goal_type": "monthly"},
            {"$set": {"target_amount": 2000.0, "is_active": True, "achieved": False}},
            upsert=True
        )
        # YEARLY (Optional but good to have)
        db.goals.update_one(
            {"user_id": uid, "goal_type": "yearly"},
            {"$set": {"target_amount": 10000.0, "is_active": True, "achieved": False}},
            upsert=True
        )
    
    print("Blanket fix complete. All Sandip accounts now have valid goals.")

if __name__ == "__main__":
    blanket_fix()
