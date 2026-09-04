"""
Cleans up old-fetch trades (no mt5_ticket) for account 433793931.
These were inserted by the Python MT5 API pull (not the EA), and
because they have no mt5_ticket the previous dedup missed them.

Strategy:
  - Group by (symbol, type, volume, net_profit, open_time) — logical deduplicate key
  - Keep the one with the highest trade_no per group
  - Delete the rest

Also shows a summary of what EA-synced trades (with mt5_ticket) exist.
"""
import sys; sys.path.insert(0, '.')
from app.mongo_database import get_db
from collections import defaultdict
from bson import ObjectId

db = get_db()
uid = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'
account = '433793931'

all_trades = list(db.trades.find({'user_id': uid, 'mt5_account': account}))
with_ticket = [t for t in all_trades if t.get('mt5_ticket')]
without_ticket = [t for t in all_trades if not t.get('mt5_ticket')]

print(f"Total trades: {len(all_trades)}")
print(f"EA-synced (has mt5_ticket): {len(with_ticket)}")
print(f"Old Python-fetch (no mt5_ticket): {len(without_ticket)}")
print()

# Dedup old-fetch trades by logical key
buckets = defaultdict(list)
for t in without_ticket:
    # Round values to avoid float comparison issues
    key = (
        t.get('symbol', ''),
        t.get('type', ''),
        round(float(t.get('volume') or 0), 4),
        round(float(t.get('net_profit') or 0), 2),
        str(t.get('open_time', ''))[:16]  # minute-level match
    )
    buckets[key].append(t)

dupe_groups = {k: v for k, v in buckets.items() if len(v) > 1}
print(f"Duplicate groups among old-fetch trades: {len(dupe_groups)}")

ids_to_delete = []
for key, group in dupe_groups.items():
    # Keep the one with the highest trade_no (most recent)
    group_sorted = sorted(group, key=lambda x: x.get('trade_no', 0), reverse=True)
    to_delete = [t['_id'] for t in group_sorted[1:]]
    ids_to_delete.extend(to_delete)

print(f"Duplicates to delete: {len(ids_to_delete)}")

if ids_to_delete:
    confirm = input(f"\nDelete {len(ids_to_delete)} duplicate old-fetch trades? (yes/no): ")
    if confirm.strip().lower() == 'yes':
        result = db.trades.delete_many({"_id": {"$in": ids_to_delete}})
        print(f"Deleted: {result.deleted_count}")
    else:
        print("Skipped.")

# Summary after cleanup
remaining = list(db.trades.find({'user_id': uid, 'mt5_account': account}))
total_np = sum(float(t.get('net_profit') or 0) for t in remaining)
print(f"\nRemaining trades: {len(remaining)}")
print(f"Total net_profit: ${total_np:.2f}")
