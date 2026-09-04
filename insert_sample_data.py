from pymongo import MongoClient
from datetime import datetime, timedelta, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)

db_name = os.getenv("DB_NAME", "JournalX")
# Fallback to finding the journal database if default name not found
if db_name not in client.list_database_names():
    for name in client.list_database_names():
        if "journal" in name.lower():
            db_name = name
            break

db = client[db_name]
print(f"Using database: {db_name}")

# Create sample events
now = datetime.now(timezone.utc)
today_str = now.strftime("%Y-%m-%d")
tomorrow_str = (now + timedelta(days=1)).strftime("%Y-%m-%d")

# Clean existing sample events to avoid duplicates
db.economic_events.delete_many({"event_id": {"$regex": "^test_"}})
print("Cleaned up old test events.")

sample_events = [
    # YESTERDAY (Past)
    {
        "event_id": "test_prev_1",
        "event_date": (now - timedelta(days=1)).strftime("%Y-%m-%d"),
        "event_time_utc": (now - timedelta(days=1)).replace(hour=14, minute=0).isoformat(),
        "country": "US",
        "currency": "USD",
        "impact_level": "medium",
        "event_name": "Fed's Balance Sheet",
        "actual": "7.5T",
        "forecast": "7.4T",
        "previous": "7.4T",
        "status": "released",
        "fetched_at": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    },
    # TODAY (Upcoming relative to UTC now, maybe passed in local)
    {
        "event_id": "test_today_1",
        "event_date": today_str,
        "event_time_utc": (now + timedelta(hours=2)).isoformat(), # 2 hours from now
        "country": "US",
        "currency": "USD",
        "impact_level": "high",
        "event_name": "CPI (MoM) (Jan)",
        "actual": None,
        "forecast": "0.3%",
        "previous": "0.2%",
        "status": "upcoming",
        "fetched_at": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    },
    {
        "event_id": "test_today_2",
        "event_date": today_str,
        "event_time_utc": (now + timedelta(hours=4)).isoformat(),
        "country": "US",
        "currency": "USD",
        "impact_level": "high",
        "event_name": "CPI (YoY) (Jan)",
        "actual": None,
        "forecast": "3.1%",
        "previous": "3.4%",
        "status": "upcoming",
        "fetched_at": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    },
    {
        "event_id": "test_today_3",
        "event_date": today_str,
        "event_time_utc": (now + timedelta(hours=6)).isoformat(),
        "country": "EU",
        "currency": "EUR",
        "impact_level": "medium",
        "event_name": "ECB President Lagarde Speaks",
        "actual": None,
        "forecast": None,
        "previous": None,
        "status": "upcoming",
        "fetched_at": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    },
    # TOMORROW
    {
        "event_id": "test_tmrw_1",
        "event_date": tomorrow_str,
        "event_time_utc": (now + timedelta(days=1, hours=10)).isoformat(),
        "country": "US",
        "currency": "USD",
        "impact_level": "high",
        "event_name": "Nonfarm Payrolls",
        "actual": None,
        "forecast": "180K",
        "previous": "175K",
        "status": "upcoming",
        "fetched_at": now.isoformat(),
        "created_at": now.isoformat(),
        "updated_at": now.isoformat()
    }
]

# Insert events
try:
    result = db.economic_events.insert_many(sample_events)
    print(f"Inserted {len(result.inserted_ids)} sample events.")
    
    # Verify count
    count = db.economic_events.count_documents({})
    print(f"Total events now: {count}")
    
except Exception as e:
    print(f"Error inserting sample data: {e}")
