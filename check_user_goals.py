from app.mongo_database import get_db

def check_user():
    db = get_db()
    user = db.users.find_one({"first_name": "Sandip"})
    if user:
        user_id = user.get('user_id')
        print(f"User Sandip found. user_id: {user_id}")
        goals = list(db.goals.find({"user_id": user_id}))
        print(f"Goals for Sandip ({user_id}): {len(goals)}")
        for g in goals:
            print(f"  - {g.get('goal_type')}: target={g.get('target_amount')}, active={g.get('is_active')}, achieved={g.get('achieved')}")
    else:
        print("User Sandip not found by first_name.")

if __name__ == "__main__":
    check_user()
