from app.mongo_database import get_db

def check_match():
    db = get_db()
    user = db.users.find_one({"first_name": "Sandip"})
    if not user:
        print("Sandip not found")
        return
    
    u_id_field = user.get("user_id")
    print(f"Sandip's user_id field: '{u_id_field}'")
    
    goals = list(db.goals.find({"user_id": u_id_field}))
    print(f"Goal match for exact string '{u_id_field}': {len(goals)}")
    
    # Check trades too
    trades = list(db.trades.find({"user_id": u_id_field}))
    print(f"Trade match for exact string '{u_id_field}': {len(trades)}")

if __name__ == "__main__":
    check_match()
