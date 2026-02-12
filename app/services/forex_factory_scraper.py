import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
import time
import re

logger = logging.getLogger(__name__)


class ForexFactoryScraper:
    """Web scraper for Forex Factory economic calendar"""
    
    BASE_URL = "https://www.forexfactory.com/calendar"
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    RATE_LIMIT_SECONDS = 30
    MAX_RETRIES = 3
    
    def __init__(self):
        self.last_request_time = 0
    
    async def scrape_calendar_page(self, start_date: str, end_date: str) -> List[Dict]:
        """
        Scrape Forex Factory calendar using Playwright
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            List of event dictionaries
        """
        events = []
        
        try:
            # Rate limiting
            await self._rate_limit()
            
            try:
                from playwright.async_api import async_playwright
            except ImportError:
                logger.warning("Playwright not found. Falling back to requests-based scrape.")
                return await self._fallback_scrape(start_date)

            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Set user agent to avoid detection
                await page.set_extra_http_headers({
                    "User-Agent": self.USER_AGENT
                })
                
                # Navigate to calendar
                url = f"{self.BASE_URL}?week={start_date}"
                logger.info(f"Scraping Forex Factory calendar: {url}")
                
                await page.goto(url, wait_until="networkidle", timeout=30000)
                
                # Wait for calendar table to load
                await page.wait_for_selector("table.calendar__table", timeout=10000)
                
                # Get page content
                content = await page.content()
                
                await browser.close()
                
                # Parse with BeautifulSoup
                events = self._parse_calendar_html(content, start_date, end_date)
                
                logger.info(f"Successfully scraped {len(events)} events")
                
        except Exception as e:
            logger.error(f"Error scraping Forex Factory: {e}")
            # Try fallback with BeautifulSoup only
            events = await self._fallback_scrape(start_date)
        
        return events
    
    def _parse_calendar_html(self, html_content: str, start_date: str, end_date: str) -> List[Dict]:
        """
        Parse HTML content to extract event data
        
        Args:
            html_content: HTML content from page
            start_date: Filter events from this date
            end_date: Filter events until this date
            
        Returns:
            List of event dictionaries
        """
        soup = BeautifulSoup(html_content, 'lxml')
        events = []
        
        # Find calendar table
        calendar_table = soup.find('table', class_='calendar__table')
        if not calendar_table:
            logger.warning("Calendar table not found in HTML")
            return events
        
        # Find all event rows
        rows = calendar_table.find_all('tr', class_='calendar__row')
        
        current_date = None
        
        for row in rows:
            try:
                # Check if this row contains a date
                date_cell = row.find('td', class_='calendar__date')
                if date_cell and date_cell.get_text(strip=True):
                    # Extract date
                    date_text = date_cell.get_text(strip=True)
                    current_date = self._parse_date(date_text)
                
                # Skip if no current date
                if not current_date:
                    continue
                
                # Extract event data
                event_data = self._parse_event_row(row, current_date)
                
                if event_data:
                    events.append(event_data)
                    
            except Exception as e:
                logger.warning(f"Error parsing row: {e}")
                continue
        
        return events
    
    def _parse_event_row(self, row, event_date: datetime) -> Optional[Dict]:
        """
        Extract event data from a table row
        
        Args:
            row: BeautifulSoup row element
            event_date: Date of the event
            
        Returns:
            Event dictionary or None
        """
        try:
            # Extract time
            time_cell = row.find('td', class_='calendar__time')
            if not time_cell:
                return None
            
            time_text = time_cell.get_text(strip=True)
            if not time_text or time_text == "All Day" or time_text == "Tentative":
                return None
            
            # Extract currency
            currency_cell = row.find('td', class_='calendar__currency')
            currency = currency_cell.get_text(strip=True) if currency_cell else "N/A"
            
            # Extract impact
            impact_cell = row.find('td', class_='calendar__impact')
            impact_level = self._normalize_impact_level(impact_cell)
            
            # Extract event name
            event_cell = row.find('td', class_='calendar__event')
            event_name = event_cell.get_text(strip=True) if event_cell else "Unknown Event"
            
            # Extract actual, forecast, previous
            actual_cell = row.find('td', class_='calendar__actual')
            forecast_cell = row.find('td', class_='calendar__forecast')
            previous_cell = row.find('td', class_='calendar__previous')
            
            actual = actual_cell.get_text(strip=True) if actual_cell else None
            forecast = forecast_cell.get_text(strip=True) if forecast_cell else None
            previous = previous_cell.get_text(strip=True) if previous_cell else None
            
            # Convert time to UTC
            event_time_utc = self._convert_to_utc(time_text, event_date)
            
            # Create unique identifier
            unique_id = self._create_unique_id(event_date, time_text, event_name)
            
            # Determine status
            status = "released" if actual and actual.strip() else "upcoming"
            
            # Extract country from currency (simplified mapping)
            country = self._get_country_from_currency(currency)
            
            return {
                "unique_id": unique_id,
                "event_date": event_date,
                "event_time_utc": event_time_utc,
                "country": country,
                "currency": currency,
                "impact_level": impact_level,
                "event_name": event_name,
                "actual": actual if actual else None,
                "forecast": forecast if forecast else None,
                "previous": previous if previous else None,
                "status": status,
                "fetched_at": datetime.utcnow()
            }
            
        except Exception as e:
            logger.warning(f"Error parsing event row: {e}")
            return None
    
    def _normalize_impact_level(self, impact_cell) -> str:
        """
        Normalize impact level to enum values
        
        Args:
            impact_cell: BeautifulSoup cell element
            
        Returns:
            Impact level: "low", "medium", or "high"
        """
        if not impact_cell:
            return "low"
        
        # Check for impact indicator spans
        impact_spans = impact_cell.find_all('span', class_='calendar__impact-icon')
        impact_count = len([s for s in impact_spans if 'calendar__impact-icon--screen' in s.get('class', [])])
        
        if impact_count >= 3:
            return "high"
        elif impact_count == 2:
            return "medium"
        else:
            return "low"
    
    def _convert_to_utc(self, time_text: str, event_date: datetime) -> datetime:
        """
        Convert event time to UTC
        
        Args:
            time_text: Time string (e.g., "8:30am", "2:00pm")
            event_date: Date of the event
            
        Returns:
            UTC datetime
        """
        try:
            # Parse time (Forex Factory uses EST/EDT)
            time_text = time_text.lower().strip()
            
            # Extract hour and minute
            match = re.match(r'(\d{1,2}):(\d{2})(am|pm)', time_text)
            if not match:
                return event_date.replace(hour=0, minute=0, second=0, microsecond=0)
            
            hour = int(match.group(1))
            minute = int(match.group(2))
            period = match.group(3)
            
            # Convert to 24-hour format
            if period == 'pm' and hour != 12:
                hour += 12
            elif period == 'am' and hour == 12:
                hour = 0
            
            # Create datetime in EST (UTC-5)
            event_datetime = event_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            # Convert EST to UTC (add 5 hours)
            # Note: This is simplified and doesn't account for DST
            event_datetime_utc = event_datetime + timedelta(hours=5)
            
            return event_datetime_utc
            
        except Exception as e:
            logger.warning(f"Error converting time to UTC: {e}")
            return event_date.replace(hour=0, minute=0, second=0, microsecond=0)
    
    def _create_unique_id(self, event_date: datetime, time_text: str, event_name: str) -> str:
        """
        Create unique identifier for event
        
        Args:
            event_date: Date of event
            time_text: Time string
            event_name: Event name
            
        Returns:
            Unique identifier string
        """
        date_str = event_date.strftime("%Y%m%d")
        time_str = time_text.replace(":", "").replace(" ", "").lower()
        name_str = re.sub(r'[^a-z0-9]', '', event_name.lower())[:30]
        
        return f"{date_str}_{time_str}_{name_str}"
    
    def _parse_date(self, date_text: str) -> Optional[datetime]:
        """
        Parse date from Forex Factory format
        
        Args:
            date_text: Date string (e.g., "Mon Jan 15")
            
        Returns:
            datetime object or None
        """
        try:
            # Forex Factory format: "Mon Jan 15" or "Jan 15"
            current_year = datetime.now().year
            
            # Try parsing with day name
            for fmt in ["%a %b %d", "%b %d"]:
                try:
                    parsed_date = datetime.strptime(date_text, fmt)
                    return parsed_date.replace(year=current_year)
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing date '{date_text}': {e}")
            return None
    
    def _get_country_from_currency(self, currency: str) -> str:
        """
        Map currency to country code
        
        Args:
            currency: Currency code
            
        Returns:
            Country code
        """
        currency_map = {
            "USD": "US",
            "EUR": "EU",
            "GBP": "GB",
            "JPY": "JP",
            "AUD": "AU",
            "CAD": "CA",
            "CHF": "CH",
            "NZD": "NZ",
            "CNY": "CN"
        }
        
        return currency_map.get(currency, currency)
    
    async def _rate_limit(self):
        """Implement rate limiting to avoid being blocked"""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.RATE_LIMIT_SECONDS:
            sleep_time = self.RATE_LIMIT_SECONDS - time_since_last_request
            logger.info(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            await asyncio.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    async def _fallback_scrape(self, start_date: str) -> List[Dict]:
        """
        Fallback scraping method using requests + BeautifulSoup
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            
        Returns:
            List of event dictionaries
        """
        try:
            import requests
            
            await self._rate_limit()
            
            # Use 'calendar.php' endpoint which is often more reliable for scraping
            # But the main /calendar URL supports ?week parameter
            url = f"{self.BASE_URL}?week={start_date}"
            headers = {
                "User-Agent": self.USER_AGENT,
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Sec-Fetch-Dest": "document",
                "Sec-Fetch-Mode": "navigate",
                "Sec-Fetch-Site": "none",
                "Sec-Fetch-User": "?1"
            }
            
            logger.info(f"Fallback scraping with requests: {url}")
            # Use a session to persist cookies if needed
            session = requests.Session()
            response = session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            logger.info(f"Response status: {response.status_code}")
            logger.info(f"Response URL: {response.url}")
            logger.info(f"Response content length: {len(response.text)}")
            logger.info(f"Response preview: {response.text[:500]}")
            
            events = self._parse_calendar_html(response.text, start_date, start_date)
            logger.info(f"Fallback scrape successful: {len(events)} events found")
            
            return events
            
        except Exception as e:
            logger.error(f"Fallback scrape failed: {e}")
            return []


# Singleton instance
forex_factory_scraper = ForexFactoryScraper()
