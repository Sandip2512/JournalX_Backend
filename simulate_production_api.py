from app.mongo_database import get_db
import json
from bson import json_util

def simulate_api():
    db = get_db()
    target_id = "e5a933cf-d99e-4b85-a2ff-379efbe82e0b"
    
    # Simulate the get_user_goals endpoint logic
    # (Copy-pasted from app/routes/goals.py)
    
    # Reactivate
    db.goals.update_many(
        {"user_id": target_id, "is_active": False, "target_amount": {"$gt": 0}},
        {"$set": {"is_active": True}}
    )
    # Fix Nulls
    db.goals.update_many(
        {"user_id": target_id, "target_amount": None},
        {"$set": {"target_amount": 0.0}}
    )
    # Ultra-Repair
    active_zeros = list(db.goals.find({"user_id": target_id, "is_active": True, "target_amount": {"$in": [0, 0.0, None]}}))
    for az in active_zeros:
        target = az.get("weekly_profit_target") or az.get("monthly_profit_target") or 0.0
        if target == 0:
            target = 500.0 if az.get("goal_type") == "weekly" else 2000.0
        db.goals.update_one({"_id": az["_id"]}, {"$set": {"target_amount": float(target)}})
        
    # Final Fetch
    goals = list(db.goals.find({"user_id": target_id, "is_active": True}))
    
    print("--- API RESPONSE SIMULATION ---")
    print(json.dumps(json.loads(json_util.dumps(goals)), indent=2))

if __name__ == "__main__":
    simulate_api()
