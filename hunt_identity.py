from app.mongo_database import get_db

def hunt_mysterious_id():
    db = get_db()
    target_id = "e5a933cf-d99e-4b85-a2ff-379efbe82e0b" # FROM LOGS
    
    print(f"HUNTING ID: {target_id}")
    
    # 1. Search in users
    user = db.users.find_one({"user_id": target_id})
    if user:
        print(f"USER FOUND: Name={user.get('first_name')}, Email={user.get('email')}")
    else:
        print("USER NOT FOUND in 'users' collection.")
        # Try finding by first name again to see ALL Sandips and their IDs
        print("\nListing all Sandips:")
        for s in db.users.find({"first_name": "Sandip"}):
            print(f" - {s.get('first_name')} | ID: {s.get('user_id')} | Email: {s.get('email')}")

    # 2. Search in goals
    goals = list(db.goals.find({"user_id": target_id}))
    print(f"\nGOALS FOUND for {target_id}: {len(goals)}")
    for g in goals:
        print(f" - Type: {g.get('goal_type')}, Target: {g.get('target_amount')}, Active: {g.get('is_active')}, ID: {g.get('_id')}")

    # 3. Search in trades (to confirm if they have trades)
    trades_count = db.trades.count_documents({"user_id": target_id})
    print(f"\nTRADES FOUND for {target_id}: {trades_count}")

if __name__ == "__main__":
    hunt_mysterious_id()
