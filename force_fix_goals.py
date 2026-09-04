from app.mongo_database import get_db

def fix_it():
    db = get_db()
    
    # 1. Total count
    total = db.goals.count_documents({})
    print(f"Total goals in DB: {total}")
    
    # 2. Find all inactive goals
    inactive = list(db.goals.find({"is_active": False}))
    print(f"Inactive goals: {len(inactive)}")
    for g in inactive:
        print(f"Inactive Goal: type={g.get('goal_type')}, achieved={g.get('achieved')}, id={g.get('id') or g.get('_id')}")
        
    # 3. Force reactivation of EVERYTHING that has a target
    result = db.goals.update_many(
        {"target_amount": {"$gt": 0}},
        {"$set": {"is_active": True}}
    )
    print(f"Reactivated {result.modified_count} goals by target check.")
    
    # 4. Check for legacy fields
    legacy = list(db.goals.find({"weekly_profit_target": {"$gt": 0}}))
    for g in legacy:
        if not g.get("target_amount"):
             # Migrate legacy to new
             db.goals.update_one({"_id": g["_id"]}, {"$set": {"target_amount": g["weekly_profit_target"], "goal_type": "weekly", "is_active": True}})
             print(f"Migrated legacy weekly goal for {g.get('user_id')}")

if __name__ == "__main__":
    fix_it()
