from app.mongo_database import get_db

def check_goals():
    db = get_db()
    goals = list(db.goals.find())
    for g in goals:
        print(f"Goal: {g.get('goal_type')}, Active: {g.get('is_active')}, Achieved: {g.get('achieved')}, Target: {g.get('target_amount')}, User: {g.get('user_id')}")

if __name__ == "__main__":
    check_goals()
