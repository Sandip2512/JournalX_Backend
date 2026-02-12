import os
import requests
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "d0sa91pr01qkkplu0drgd0sa91pr01qkkplu0ds0")
FINNHUB_BASE_URL = "https://finnhub.io/api/v1/calendar/economic"

def fetch_finnhub_events(start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
    """
    Fetch economic events from Finnhub API
    """
    if not FINNHUB_API_KEY:
        logger.error("FINNHUB_API_KEY not found in environment")
        return []

    # Default to current week if dates not provided
    if not start_date or not end_date:
        today = datetime.now()
        start_date = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        end_date = (today + timedelta(days=6-today.weekday())).strftime("%Y-%m-%d")

    params = {
        "token": FINNHUB_API_KEY,
        "from": start_date,
        "to": end_date
    }

    try:
        logger.info(f"Fetching Finnhub events from {start_date} to {end_date}")
        response = requests.get(FINNHUB_BASE_URL, params=params, timeout=15)
        
        if response.status_code == 403:
            logger.warning("Finnhub Economic Calendar access restricted (403 Forbidden).")
            return []
            
        response.raise_for_status()
        data = response.json()
        
        finnhub_events = data.get("economicCalendar", [])
        events = []
        
        for item in finnhub_events:
            try:
                # Map Finnhub fields to our internal schema
                # Finnhub time is usually in local time of the event, but we prefer UTC
                # However, Finnhub JSON doesn't always provide a clear UTC timestamp for all events
                # We'll use what's available and normalize it.
                
                event_name = item.get("event", "Economic Event")
                country = item.get("country", "")
                currency = item.get("unit", "") # Finnhub unit often contains currency or %
                
                # Impact mapping
                impact = item.get("impact", "low").lower()
                if impact not in ["low", "medium", "high"]:
                    impact = "low"
                
                # Clean values
                actual = str(item.get("actual")) if item.get("actual") is not None else ""
                forecast = str(item.get("forecast")) if item.get("forecast") is not None else ""
                previous = str(item.get("previous")) if item.get("previous") is not None else ""
                
                # Date and Time
                # Finnhub provides 'time' as HH:MM and relies on the request's 'from' to 'to'
                # For simplicity, we'll try to find a date if possible or use the current day logic
                # Actually, Finnhub usually returns 'time' like '2026-02-13 13:30:00' if it's a timestamp
                
                # Generate unique ID
                timestamp_str = item.get("time", "")
                unique_id = f"fh_{country}_{timestamp_str.replace(' ', '_').replace(':', '')}_{event_name.replace(' ', '_')}"
                
                # Parse date and time
                try:
                    dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
                except:
                    # Fallback if format is different
                    dt = datetime.now() 

                events.append({
                    "unique_id": unique_id,
                    "event_date": dt.replace(hour=0, minute=0, second=0, microsecond=0),
                    "event_time_utc": dt,
                    "country": country,
                    "currency": currency,
                    "impact_level": impact,
                    "event_name": event_name,
                    "actual": actual,
                    "forecast": forecast,
                    "previous": previous,
                    "status": "released" if actual else "upcoming",
                    "fetched_at": datetime.utcnow()
                })
            except Exception as e:
                logger.error(f"Error parsing Finnhub event: {e}")
                continue
                
        return events

    except Exception as e:
        logger.error(f"Error fetching Finnhub events: {e}")
        return []
