import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pymongo.database import Database
try:
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    HAS_SCHEDULER = True
except ImportError:
    HAS_SCHEDULER = False

from app.services.forex_factory_scraper import forex_factory_scraper
from app.services.fair_economy_service import fetch_fair_economy_events
from app.services.finnhub_service import fetch_finnhub_events

logger = logging.getLogger(__name__)

# Initialize scheduler if available
scheduler = AsyncIOScheduler() if HAS_SCHEDULER else None


class EconomicCalendarService:
    """Service for managing economic calendar data"""
    
    def __init__(self):
        self.scheduler_started = False
    
    async def sync_events_to_db(self, db: Database, events: List[Dict]) -> Dict[str, int]:
        """
        Store or update scraped events in MongoDB
        
        Args:
            db: MongoDB database instance
            events: List of event dictionaries
            
        Returns:
            Dictionary with counts: {created, updated, skipped}
        """
        created = 0
        updated = 0
        skipped = 0
        
        if not events:
            print("DEBUG: sync_events_to_db received empty events list")
            return {"created": 0, "updated": 0, "skipped": 0, "total": 0}

        print(f"DEBUG: Syncing {len(events)} events to DB...")
        
        for event in events:
            try:
                # print(f"Processing event: {event.get('unique_id')}")
                # Check if event exists
                existing = db.economic_events.find_one({"unique_id": event["unique_id"]})
                
                if existing:
                    print(f"DEBUG: Found existing for {event['unique_id']}: {existing.get('_id')} - {existing.get('event_name')}")
                    # Update if actual/forecast/previous changed
                    update_fields = {}
                    
                    if event.get("actual") != existing.get("actual"):
                        update_fields["actual"] = event.get("actual")
                    
                    if event.get("forecast") != existing.get("forecast"):
                        update_fields["forecast"] = event.get("forecast")
                    
                    if event.get("previous") != existing.get("previous"):
                        update_fields["previous"] = event.get("previous")
                    
                    if event.get("status") != existing.get("status"):
                        update_fields["status"] = event.get("status")
                    
                    if update_fields:
                        update_fields["updated_at"] = datetime.utcnow()
                        update_fields["fetched_at"] = event.get("fetched_at")
                        
                        db.economic_events.update_one(
                            {"unique_id": event["unique_id"]},
                            {"$set": update_fields}
                        )
                        updated += 1
                    else:
                        skipped += 1
                else:
                    # Create new event
                    event["created_at"] = datetime.utcnow()
                    event["updated_at"] = datetime.utcnow()
                    
                    db.economic_events.insert_one(event)
                    created += 1
                    
            except Exception as e:
                logger.error(f"Error syncing event {event.get('unique_id')}: {e}")
                continue
        
        logger.info(f"Sync complete: {created} created, {updated} updated, {skipped} skipped")
        
        return {
            "created": created,
            "updated": updated,
            "skipped": skipped,
            "total": len(events)
        }
    
    def get_events_with_filters(
        self,
        db: Database,
        user_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        currencies: Optional[List[str]] = None,
        impacts: Optional[List[str]] = None,
        high_impact_only: bool = False,
        search_query: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """
        Retrieve events with filters and user-specific data
        
        Args:
            db: MongoDB database instance
            user_id: User ID
            start_date: Filter from this date
            end_date: Filter until this date
            currencies: List of currency codes
            impacts: List of impact levels
            high_impact_only: Show only high impact events
            search_query: Search in event names
            status: Event status filter
            
        Returns:
            List of event dictionaries with user data
        """
        # Build query
        query = {}
        
        # Date range filter
        if start_date or end_date:
            query["event_date"] = {}
            if start_date:
                query["event_date"]["$gte"] = start_date
            if end_date:
                query["event_date"]["$lte"] = end_date
        
        # Currency filter
        if currencies:
            query["currency"] = {"$in": currencies}
        
        # Impact filter
        if high_impact_only:
            query["impact_level"] = "high"
        elif impacts:
            query["impact_level"] = {"$in": impacts}
        
        # Search query
        if search_query:
            query["event_name"] = {"$regex": search_query, "$options": "i"}
        
        # Status filter
        if status:
            query["status"] = status
        
        # Fetch events
        events = list(db.economic_events.find(query).sort("event_time_utc", 1))
        
        # Enrich with user-specific data
        for event in events:
            event["_id"] = str(event["_id"])
            
            # Check if marked as important
            mark = db.user_event_marks.find_one({
                "user_id": user_id,
                "event_id": event["_id"]
            })
            event["is_marked"] = mark.get("is_marked", False) if mark else False
            
            # Count notes
            notes_count = db.event_notes.count_documents({
                "user_id": user_id,
                "event_id": event["_id"]
            })
            event["notes_count"] = notes_count
            
            # Count linked trades
            links_count = db.event_trade_links.count_documents({
                "user_id": user_id,
                "event_id": event["_id"]
            })
            event["linked_trades_count"] = links_count
        
        return events
    
    def convert_to_user_timezone(self, event: Dict, timezone_offset: float) -> Dict:
        """
        Convert event time to user timezone
        
        Args:
            event: Event dictionary
            timezone_offset: Timezone offset in hours from UTC
            
        Returns:
            Event with converted time
        """
        if "event_time_utc" in event:
            utc_time = event["event_time_utc"]
            user_time = utc_time + timedelta(hours=timezone_offset)
            event["event_time_local"] = user_time
        
        return event
    
    def calculate_next_high_impact(self, db: Database) -> Optional[Dict]:
        """
        Find next high-impact event for countdown
        
        Args:
            db: MongoDB database instance
            
        Returns:
            Next high-impact event or None
        """
        now = datetime.utcnow()
        
        next_event = db.economic_events.find_one({
            "impact_level": "high",
            "event_time_utc": {"$gte": now},
            "status": "upcoming"
        }, sort=[("event_time_utc", 1)])
        
        if next_event:
            next_event["_id"] = str(next_event["_id"])
        
        return next_event
    
    async def update_event_status(self, db: Database):
        """
        Update status of events to 'released' when actual value is available
        
        Args:
            db: MongoDB database instance
        """
        result = db.economic_events.update_many(
            {
                "status": "upcoming",
                "actual": {"$ne": None, "$ne": ""}
            },
            {
                "$set": {
                    "status": "released",
                    "updated_at": datetime.utcnow()
                }
            }
        )
        
        if result.modified_count > 0:
            logger.info(f"Updated {result.modified_count} events to 'released' status")
    
    async def auto_update_calendar(self, db: Database):
        """
        Auto-update job to fetch latest events
        Runs every 30 minutes
        """
        logger.info("Starting auto-update of economic calendar")
        
        try:
            import asyncio
            
            # Step 1: Try Finnhub First (Best for actuals)
            logger.info("Attempting to fetch data from Finnhub API...")
            loop = asyncio.get_event_loop()
            events = await loop.run_in_executor(None, fetch_finnhub_events)
            
            # Step 2: Fallback to FairEconomy if Finnhub yields no results (e.g., 403 or empty)
            if not events:
                logger.warning("Finnhub returned no events. Falling back to FairEconomy XML feed...")
                events = await loop.run_in_executor(None, fetch_fair_economy_events)
            
            if not events:
                logger.warning("No events fetched from any source (Finnhub or FairEconomy)")
                return

            logger.info(f"Fetched {len(events)} events. Syncing to database...")
            
            # Sync to database
            result = await self.sync_events_to_db(db, events)
            
            # Update event statuses based on time (if sources lack real-time actuals)
            await self.update_event_status_by_time(db)
            
            logger.info(f"Auto-update complete: {result}")
            
        except Exception as e:
            logger.error(f"Auto-update failed: {e}")
            import traceback
            traceback.print_exc()

    async def update_event_status_by_time(self, db: Database):
        """
        Update status to 'released' if time has passed, even without actuals
        """
        now = datetime.utcnow()
        result = db.economic_events.update_many(
            {
                "status": "upcoming",
                "event_time_utc": {"$lt": now.isoformat()},
                "actual": {"$in": [None, ""]}  # Only if no actual data yet
            },
            {
                "$set": {
                    "status": "released",
                    "updated_at": now
                }
            }
        )
        if result.modified_count > 0:
            logger.info(f"Marked {result.modified_count} past events as Released")
    
    def start_scheduler(self, db: Database):
        """
        Start the auto-update scheduler
        
        Args:
            db: MongoDB database instance
        """
        if not HAS_SCHEDULER or not scheduler:
            logger.warning("Scheduler not available. Skipping auto-update initialization.")
            return

        if self.scheduler_started:
            logger.warning("Scheduler already started")
            return
        
        # Add job to run every 30 minutes
        scheduler.add_job(
            self.auto_update_calendar,
            'interval',
            minutes=30,
            args=[db],
            id='calendar_auto_update',
            replace_existing=True
        )
        
        # Run immediately on startup
        scheduler.add_job(
            self.auto_update_calendar,
            'date',
            run_date=datetime.now() + timedelta(seconds=10),
            args=[db],
            id='calendar_initial_fetch'
        )
        
        scheduler.start()
        self.scheduler_started = True
        
        logger.info("Economic calendar auto-update scheduler started")
    
    def stop_scheduler(self):
        """Stop the auto-update scheduler"""
        if HAS_SCHEDULER and scheduler and scheduler.running:
            scheduler.shutdown()
            self.scheduler_started = False
            logger.info("Economic calendar scheduler stopped")


# Singleton instance
economic_calendar_service = EconomicCalendarService()
