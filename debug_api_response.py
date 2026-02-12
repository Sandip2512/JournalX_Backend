import sys
import os
import logging
from datetime import datetime, timedelta

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add Backend to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mongo_database import get_db
from app.services.economic_calendar_service import economic_calendar_service

def debug_api():
    try:
        logger.info("Connecting to DB...")
        db = get_db()
        logger.info(f"Connected to DB: {db.name}")
        
        # 1. Check DB Content
        count = db.economic_events.count_documents({})
        logger.info(f"Total events in DB: {count}")
        
        if count == 0:
            logger.warning("DB is empty! Sync failed.")
            return

        # 2. Check Date Range of Events in DB
        first_event = db.economic_events.find_one(sort=[("event_time_utc", 1)])
        last_event = db.economic_events.find_one(sort=[("event_time_utc", -1)])
        
        if first_event:
            logger.info(f"First Event in DB: {first_event['event_time_utc']} ({first_event['event_name']})")
        if last_event:
            logger.info(f"Last Event in DB: {last_event['event_time_utc']} ({last_event['event_name']})")
            
        # 3. Simulate API Request for TODAY (Feb 13)
        # Frontend requests: start_date=today (00:00), end_date=today (23:59)
        # BUT timezone matters. Frontend sends user local time.
        # User is likely IST (+5:30).
        # Feb 13 00:00 IST = Feb 12 18:30 UTC.
        # Feb 13 23:59 IST = Feb 13 18:29 UTC.
        
        start_date = datetime(2026, 2, 12, 18, 30)
        end_date = datetime(2026, 2, 13, 18, 29)
        
        logger.info(f"Simulating API request for Today (IST -> UTC): {start_date} to {end_date}")
        
        events = economic_calendar_service.get_events_with_filters(
            db=db,
            user_id="test_user",
            start_date=start_date,
            end_date=end_date
        )
        
        logger.info(f"API returned {len(events)} events.")
        for e in events:
            logger.info(f" - {e['event_time_utc']}: {e['event_name']}")
            
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_api()
