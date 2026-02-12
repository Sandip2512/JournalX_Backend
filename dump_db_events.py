import sys
import os
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mongo_database import get_db

def dump_events():
    try:
        db = get_db()
        print(f"DB Name: {db.name}", flush=True)
        try:
            print(f"DB Client Address: {db.client.address}", flush=True)
        except:
             print("DB Client Address: Unknown", flush=True)
        
        count = db.economic_events.count_documents({})
        print(f"Total events: {count}", flush=True)
        
        # Dump all events sorted by time
        events = list(db.economic_events.find().sort("event_time_utc", 1))
        
        print("\n--- Events Dump ---")
        for e in events:
            # Print unique_id, time, name
            print(f"[{e.get('event_time_utc')}] {e.get('event_name')} (ID: {e.get('unique_id')})")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    dump_events()
