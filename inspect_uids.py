import sys
sys.path.insert(0, '.')
from app.mongo_database import get_db

db = get_db()

print('=== USERS ===')
for u in db.users.find():
    uid = u.get('user_id', str(u['_id']))
    tc = db.trades.count_documents({'user_id': uid})
    print(f'  uid={uid}  email={u.get("email", "")}  trades={tc}')

print()
print('=== TRADE UIDs ===')
for uid in db.trades.distinct('user_id'):
    tc = db.trades.count_documents({'user_id': uid})
    user = db.users.find_one({'user_id': uid})
    print(f'  uid={uid}  count={tc}  in_users={user is not None}')

print()
print('=== MT5 CREDS ===')
for c in db.mt5_credentials.find():
    print(f'  user_id={c.get("user_id")}  account={c.get("account")}')
