from app.mongo_database import get_db

def find_sandip_goals():
    db = get_db()
    sandip = db.users.find_one({"first_name": "Sandip"})
    if not sandip:
        print("Sandip not found")
        return
    
    user_id = sandip.get("user_id")
    obj_id = str(sandip.get("_id"))
    print(f"Sandip UserID: {user_id}")
    print(f"Sandip ObjID: {obj_id}")
    
    print("\n--- Goals for UserID ---")
    goals_u = list(db.goals.find({"user_id": user_id}))
    for g in goals_u:
        print(f"G_ID: {g.get('_id')}, Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, Active: {g.get('is_active')}, LegacyW: {g.get('weekly_profit_target')}")
        
    print("\n--- Goals for ObjID ---")
    goals_o = list(db.goals.find({"user_id": obj_id}))
    for g in goals_o:
        print(f"G_ID: {g.get('_id')}, Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, Active: {g.get('is_active')}, LegacyW: {g.get('weekly_profit_target')}")

if __name__ == "__main__":
    find_sandip_goals()
