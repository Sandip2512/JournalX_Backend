from app.mongo_database import get_db

def audit_sandips():
    db = get_db()
    
    # 1. Find all users named Sandip
    users = list(db.users.find({"first_name": "Sandip"}))
    print(f"Found {len(users)} users named Sandip.")
    for u in users:
        u_id = u.get("user_id")
        obj_id = str(u.get("_id"))
        email = u.get("email")
        print(f"User: {u.get('first_name')} | Email: {email} | UUID: {u_id} | OBJID: {obj_id}")
        
        # Check goals for this user
        goals = list(db.goals.find({"user_id": u_id}))
        print(f"  -> Goals for UUID {u_id}: {len(goals)}")
        for g in goals:
            print(f"     - Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, Active: {g.get('is_active')}, G_ID: {g.get('_id')}")
            
        # Check goals for OBJID (just in case)
        goals_obj = list(db.goals.find({"user_id": obj_id}))
        if goals_obj:
            print(f"  -> Goals for OBJID {obj_id}: {len(goals_obj)}")

if __name__ == "__main__":
    audit_sandips()
