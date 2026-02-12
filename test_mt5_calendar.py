import MetaTrader5 as mt5
from datetime import datetime, timedelta
import sys

def test_calendar():
    if not mt5.initialize():
        print("initialize() failed, error code =", mt5.last_error())
        return

    print(f"MT5 Initialized. Version: {mt5.version()}")
    
    # Check if calendar functions exist
    if not hasattr(mt5, 'calendar_value_history'):
        print("ERROR: mt5.calendar_value_history function NOT found.")
        print("Available functions:", dir(mt5))
        mt5.shutdown()
        return

    # Get events for the last 2 days and next 2 days
    now = datetime.now()
    date_from = now - timedelta(days=2)
    date_to = now + timedelta(days=2)
    
    print(f"Fetching calendar data from {date_from} to {date_to}...")
    
    try:
        # Check if country_codes needed
        values = mt5.calendar_value_history(date_from, date_to)
        if values is None:
            print(f"mt5.calendar_value_history returned None. Error: {mt5.last_error()}")
        else:
            print(f"Found {len(values)} calendar values.")
            
    except Exception as e:
        print(f"Error calling calendar_value_history: {e}")
        import traceback
        traceback.print_exc()

    try:
        events = mt5.calendar_events()
        if events is None:
            print(f"mt5.calendar_events returned None. Error: {mt5.last_error()}")
        else:
            print(f"Found {len(events)} events.")
            
    except Exception as e:
        print(f"Error calling calendar_events: {e}")

    mt5.shutdown()

if __name__ == "__main__":
    test_calendar()
