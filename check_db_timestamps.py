from app.mongo_database import get_db
from datetime import datetime, timezone
import json

def check_today_events():
    db = get_db()
    # Check all events
    events = list(db.economic_events.find().sort("event_time_utc", 1))
    
    print(f"Total events in DB: {len(events)}")
    
    # Check current time
    now_utc = datetime.now(timezone.utc)
    print(f"Current UTC time: {now_utc}")
    
    print("\nSample Events (Next 10 from now):")
    upcoming = db.economic_events.find({"event_time_utc": {"$gte": now_utc}}).sort("event_time_utc", 1).limit(10)
    for e in upcoming:
        print(f"[{e.get('event_time_utc')}] {e.get('event_name')} ({e.get('country')}) - ID: {e.get('unique_id')}")

    print("\nRecent Past Events (Last 10):")
    past = db.economic_events.find({"event_time_utc": {"$lt": now_utc}}).sort("event_time_utc", -1).limit(10)
    for e in past:
        print(f"[{e.get('event_time_utc')}] {e.get('event_name')} ({e.get('country')}) - ID: {e.get('unique_id')}")

if __name__ == "__main__":
    check_today_events()
