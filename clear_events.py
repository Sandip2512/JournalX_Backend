from app.mongo_database import get_db

def clear_events():
    db = get_db()
    # Keep sample events, delete others
    # Sample events have IDs like sample_1_...
    result = db.economic_events.delete_many({
        "unique_id": {"$regex": "^(ff_|fh_)"}
    })
    print(f"Deleted {result.deleted_count} events (Finnhub and FairEconomy).")

if __name__ == "__main__":
    clear_events()
