from app.mongo_database import get_db
from app.routes.goals import get_user_goals

def check_api():
    db = get_db()
    user_id = "b95f9a4b-c79c-4168-9de5-a2ff379efbe8"
    goals = get_user_goals(user_id, db)
    print(f"API Returned {len(goals)} goals for {user_id}")
    for g in goals:
        # g is a dict or model
        print(f"  - {g.get('goal_type')}: {g.get('target_amount')}")

if __name__ == "__main__":
    check_api()
