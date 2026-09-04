import sys
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add Backend to sys.path to allow 'from app...' imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mongo_database import get_db
from app.services.economic_calendar_service import economic_calendar_service
import asyncio
from dotenv import load_dotenv

load_dotenv()

async def trigger():
    try:
        logger.info("Connecting to DB...")
        db = get_db()
        logger.info(f"Connected to DB: {db.name}")
        
        # Test fetch directly
        from app.services.fair_economy_service import fetch_fair_economy_events
        logger.info("Testing fetch_fair_economy_events directly...")
        events = fetch_fair_economy_events()
        logger.info(f"Direct fetch found {len(events)} events.")
        
        if events:
            logger.info(f"First event: {events[0]}")
        
        logger.info("Triggering auto_update_calendar...")
        await economic_calendar_service.auto_update_calendar(db)
        logger.info("Update triggered.")
        
        # Check count
        count = db.economic_events.count_documents({})
        logger.info(f"Total events in DB: {count}")
        
        # Check if any new events with unique_id starting with 'ff_'
        ff_count = db.economic_events.count_documents({"unique_id": {"$regex": "^ff_"}})
        logger.info(f"FairEconomy events in DB: {ff_count}")
        
        # Check a few events
        events = list(db.economic_events.find().sort("created_at", -1).limit(5))
        for e in events:
            logger.info(f"Event: {e.get('event_name')} ({e.get('event_date')}) ID: {e.get('unique_id')}")
    
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(trigger())
