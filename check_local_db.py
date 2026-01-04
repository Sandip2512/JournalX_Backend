from app.mongo_database import get_db

db = get_db()
print("--- LOCAL USERS (Sandip) ---")
for u in db.users.find({"first_name": "Sandip"}):
    print(f"Name: {u.get('first_name')} | ID: {u.get('user_id')}")

print("\n--- LOCAL GOALS ---")
for g in db.goals.find():
    print(f"User: {g.get('user_id')} | Type: {g.get('goal_type')} | Target: {g.get('target_amount')} | Active: {g.get('is_active')}")
