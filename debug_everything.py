from app.mongo_database import get_db

db = get_db()
print("--- ALL USERS IN DB ---")
for u in db.users.find():
    print(f"Name: {u.get('first_name')} {u.get('last_name')} | ID: {u.get('user_id')} | Email: {u.get('email')}")
