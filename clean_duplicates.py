import sys
sys.path.insert(0, '.')
from app.mongo_database import get_db

db = get_db()
print('Finding duplicate users...')
users = list(db.users.find({'email': 'anshit028@gmail.com'}))
print('Users found:', len(users))

# Identify which one has the trades, which one has the creds
for u in users:
    uid = u.get('user_id', str(u.get('_id', '')))
    tc = db.trades.count_documents({'user_id': uid})
    cc = db.mt5_credentials.count_documents({'user_id': uid})
    print(f'uid: {uid}, trades: {tc}, creds: {cc}')

uid1 = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'
uid2 = 'faa2b081-d51b-4a39-8fcb-c12e873ca994'

# In our previous investigation, e5a933cf had creds, faa2b081 had trades.
# But wait! I tried migrating 103 orphans to e5a9 earlier, maybe it DID work?
# Let's count them explicitly.
tc1 = db.trades.count_documents({'user_id': uid1})
tc2 = db.trades.count_documents({'user_id': uid2})

primary_uid = uid1 if cc > 0 else uid2 # we want the one with credentials to be primary

print(f'\nMigrating trades to {primary_uid}...')
# Move from uid2 to uid1
result1 = db.trades.update_many({'user_id': uid2}, {'$set': {'user_id': primary_uid}})
print('Migrated from uid2:', result1.modified_count)

# Clean up duplicate user record
db.users.delete_one({'user_id': uid2})
print('Deleted redundant user record', uid2)
