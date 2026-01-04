from app.mongo_database import get_db

def final_fix():
    db = get_db()
    # Find all users
    users = list(db.users.find())
    for user in users:
        u_id = user.get("user_id")
        if not u_id: continue
        
        print(f"Checking goals for User: {user.get('first_name')} ({u_id})")
        
        # Find any goals for this user
        goals = list(db.goals.find({"user_id": u_id}))
        
        # If no goals, check if they exist under ObjectId string or other formats
        if not goals:
            obj_id = str(user.get("_id"))
            goals = list(db.goals.find({"user_id": obj_id}))
            if goals:
                print(f"Migrating goals from ObjectId {obj_id} to UUID {u_id}")
                db.goals.update_many({"user_id": obj_id}, {"$set": {"user_id": u_id}})
        
        # Standardize existing goals
        for g in goals:
            updates = {"is_active": True}
            
            # Migrate legacy field names
            if not g.get("target_amount"):
                if g.get("weekly_profit_target"):
                    updates["target_amount"] = g.get("weekly_profit_target")
                    updates["goal_type"] = "weekly"
                elif g.get("monthly_profit_target"):
                    updates["target_amount"] = g.get("monthly_profit_target")
                    updates["goal_type"] = "monthly"
            
            # Ensure goal_type is set
            if not g.get("goal_type"):
                # Default to monthly if unknown
                updates["goal_type"] = "monthly"
                
            db.goals.update_one({"_id": g["_id"]}, {"$set": updates})
            print(f"Updated goal {g.get('_id')} for {user.get('first_name')}")

if __name__ == "__main__":
    final_fix()
