import asyncio
import logging
import sys
import os
from datetime import datetime, timedelta
from app.services.forex_factory_scraper import forex_factory_scraper
from app.services.economic_calendar_service import economic_calendar_service
from app.mongo_database import db_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_scraper_manual():
    """Manually run the scraper"""
    try:
        print("Connecting to database...")
        db = db_client.connect()
        print(f"Connected to {db.name}")
        
        print("Starting scrape...")
        start_date = datetime.now()
        end_date = start_date + timedelta(days=7)
        
        events = await forex_factory_scraper.scrape_calendar_page(
            start_date.strftime("%Y-%m-%d"),
            end_date.strftime("%Y-%m-%d")
        )
        
        print(f"Scraped {len(events)} events.")
        
        if len(events) > 0:
            print("Syncing to database...")
            result = await economic_calendar_service.sync_events_to_db(db, events)
            print(f"Sync result: {result}")
        else:
            print("No events found to sync.")
            
    except Exception as e:
        print(f"Error running scraper: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    
    asyncio.run(run_scraper_manual())
