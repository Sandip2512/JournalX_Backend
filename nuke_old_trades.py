import sys; sys.path.insert(0, '.')
from app.mongo_database import get_db
db = get_db()
uid = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'
account = '433793931'

# Find all trades for this account
all_trades = list(db.trades.find({'user_id': uid, 'mt5_account': account}))

# Filter trades lacking mt5_ticket
without_ticket = [t['_id'] for t in all_trades if not t.get('mt5_ticket')]

print(f"Total trades for account: {len(all_trades)}")
print(f"Trades without mt5_ticket to delete: {len(without_ticket)}")

if without_ticket:
    res = db.trades.delete_many({"_id": {"$in": without_ticket}})
    print(f"Deleted {res.deleted_count} trades.")
    
# Remaining PNL
remaining = list(db.trades.find({'user_id': uid, 'mt5_account': account}))
total_np = sum(float(t.get('net_profit') or 0) for t in remaining)
print(f"\nRemaining trades: {len(remaining)}")
print(f"Total net_profit: ${total_np:.2f}")
