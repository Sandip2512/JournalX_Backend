import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

FEED_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"

def fetch_fair_economy_events() -> List[Dict[str, Any]]:
    """
    Fetches events from FairEconomy XML feed.
    Times are in GMT (UTC).
    """
    try:
        response = requests.get(FEED_URL, timeout=10)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        events = []
        
        for event in root.findall('event'):
            try:
                title = event.find('title').text
                country = event.find('country').text
                date_str = event.find('date').text  # MM-DD-YYYY
                time_str = event.find('time').text  # e.g. 1:30pm or 24hr?
                impact = event.find('impact').text
                forecast = event.find('forecast').text or ""
                previous = event.find('previous').text or ""
                
                # Parse DateTime (GMT)
                # Format: 02-12-2026 1:30pm
                dt_str = f"{date_str} {time_str}"
                
                # Handle time format variations usually 1:30pm or 11:30pm
                # But sometimes it might be 24h? XML sample showed "1:30pm".
                # Also "12:00am".
                try:
                    dt = datetime.strptime(dt_str, "%m-%d-%Y %I:%M%p")
                except ValueError:
                    # Fallback or log?
                    # Try 24h just in case? Or simple time
                    logger.warning(f"Could not parse date/time: {dt_str}")
                    continue
                
                # Create ID
                event_id = f"ff_{country}_{dt.strftime('%Y%m%d_%H%M')}_{title[:10].replace(' ', '_')}"
                
                events.append({
                    "unique_id": event_id,
                    "event_name": title,
                    "event_date": dt.replace(hour=0, minute=0, second=0, microsecond=0),
                    "event_time_utc": dt,
                    "country": country,
                    "currency": country,
                    "impact_level": impact.lower(),
                    "actual": "",
                    "forecast": forecast,
                    "previous": previous,
                    "status": "upcoming" if dt > datetime.utcnow() else "released",
                    "fetched_at": datetime.utcnow()
                })
                
            except Exception as e:
                logger.warning(f"Error parsing event: {e}")
                continue
                
        logger.info(f"Fetched {len(events)} events from FairEconomy")
        return events
        
    except Exception as e:
        logger.error(f"Failed to fetch FairEconomy feed: {e}")
        return []
