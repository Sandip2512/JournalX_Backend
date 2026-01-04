from app.mongo_database import get_db
import json
from bson import json_util

def deep_scan():
    db = get_db()
    # Find ALL goals to identify any potential issues
    all_goals = list(db.goals.find())
    print("--- ALL GOALS IN DB ---")
    for g in all_goals:
        print(f"ID: {g.get('_id')}, User: {g.get('user_id')}, Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, LegacyW: {g.get('weekly_profit_target')}, Active: {g.get('is_active')}")
    
    # Find all users to match IDs
    all_users = list(db.users.find({}, {"user_id": 1, "first_name": 1, "email": 1}))
    print("\n--- ALL USERS IN DB ---")
    for u in all_users:
        print(f"Name: {u.get('first_name')}, UserID: {u.get('user_id')}, ObjID: {u.get('_id')}")

if __name__ == "__main__":
    deep_scan()
