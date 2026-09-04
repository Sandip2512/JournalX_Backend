from app.mongo_database import get_db

def check_types():
    db = get_db()
    goal = db.goals.find_one({"user_id": "b95f9a4b-c79c-4168-9de5-a2ff379efbe8"})
    if goal:
        print(f"Goal Found. is_active: {goal.get('is_active')} (type: {type(goal.get('is_active'))})")
        print(f"Goal Found. user_id: {goal.get('user_id')} (type: {type(goal.get('user_id'))})")
    else:
        print("No goal found for that user_id")

if __name__ == "__main__":
    check_types()
