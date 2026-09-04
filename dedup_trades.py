"""
Deduplication script: removes duplicate trades that were created by the
MT5 reconnect bug (same mt5_ticket inserted multiple times for the same user).

For each (user_id, mt5_ticket) bucket with > 1 doc, keeps the one with the
highest trade_no (most recent insert) and deletes the rest.
"""
import sys
sys.path.insert(0, '.')
from app.mongo_database import get_db
from bson import ObjectId

db = get_db()
uid = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'

print("=== Dedup: grouping by mt5_ticket ===")

pipeline = [
    {"$match": {"user_id": uid, "mt5_ticket": {"$exists": True, "$ne": None}}},
    {"$sort": {"trade_no": -1}},   # highest trade_no = most recent insert
    {"$group": {
        "_id": "$mt5_ticket",
        "count": {"$sum": 1},
        "keep_id": {"$first": "$_id"},      # keep the first (highest trade_no)
        "all_ids": {"$push": "$_id"}
    }},
    {"$match": {"count": {"$gt": 1}}}       # only buckets with duplicates
]

groups = list(db.trades.aggregate(pipeline))
print(f"Buckets with duplicates: {len(groups)}")

total_deleted = 0
for g in groups:
    ids_to_delete = [oid for oid in g["all_ids"] if oid != g["keep_id"]]
    result = db.trades.delete_many({"_id": {"$in": ids_to_delete}})
    total_deleted += result.deleted_count
    print(f"  ticket={g['_id']} dupes={g['count']-1} → deleted {result.deleted_count}")

print(f"\nTotal duplicates deleted: {total_deleted}")

# Verify
remaining = db.trades.count_documents({"user_id": uid})
print(f"Trades remaining for user: {remaining}")
total_np = sum(float(t.get("net_profit") or 0) for t in db.trades.find({"user_id": uid}))
print(f"Total net_profit after dedup: {total_np:.2f}")
