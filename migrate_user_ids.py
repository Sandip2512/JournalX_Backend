import sys
sys.path.insert(0, '.')
from app.mongo_database import get_db

db = get_db()

# Get trades user_ids that do NOT exist in users table
trade_uids = db.trades.distinct('user_id')
user_map = {u['user_id']: u for u in db.users.find() if u.get('user_id')}

orphaned_uids = [uid for uid in trade_uids if uid not in user_map]
valid_uids = [uid for uid in trade_uids if uid in user_map]

print("Orphaned trade UIDs (no user record):", orphaned_uids)
print("Valid trade UIDs (has user record):", valid_uids)

# For the mt5_credentials: the cred user_id should be the canonical user
all_creds = list(db.mt5_credentials.find())
print()
print("MT5 Creds user_ids:", [c.get('user_id') for c in all_creds])

# Strategy: for each orphaned trade uid, assign all those trades to the
# user_id found in mt5_credentials (the connected account owner)
if len(all_creds) == 1 and len(orphaned_uids) == 1:
    new_uid = all_creds[0]['user_id']
    old_uid = orphaned_uids[0]
    if old_uid == new_uid:
        print("No migration needed - already same uid")
    else:
        r = db.trades.update_many({'user_id': old_uid}, {'$set': {'user_id': new_uid}})
        print(f"Migrated {r.modified_count} trades: {old_uid} -> {new_uid}")
elif len(orphaned_uids) == 0:
    print("No orphaned trades found. All trades are correctly tied to users.")
else:
    # Try matching by mt5_credentials to trade mt5_account field
    for cred in all_creds:
        cred_uid = cred['user_id']
        cred_account = str(cred.get('account', ''))
        for orphan in orphaned_uids:
            sample = db.trades.find_one({'user_id': orphan, 'mt5_account': cred_account})
            if sample:
                r = db.trades.update_many({'user_id': orphan}, {'$set': {'user_id': cred_uid}})
                print(f"Matched via mt5_account. Migrated {r.modified_count} trades: {orphan} -> {cred_uid}")
                break

print("\nAfter migration:")
for u in db.users.find():
    uid = u.get('user_id', str(u['_id']))
    tc = db.trades.count_documents({'user_id': uid})
    print(f"  user={uid}  trades={tc}")
