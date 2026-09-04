import requests
import json
from datetime import datetime, timedelta

API_KEY = "d0sa91pr01qkkplu0drgd0sa91pr01qkkplu0ds0"
URL = "https://finnhub.io/api/v1/calendar/economic"

def test_finnhub():
    # Fetch events for the current week
    today = datetime.now()
    start_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=5)).strftime("%Y-%m-%d")
    
    params = {
        "token": API_KEY,
        "from": start_date,
        "to": end_date
    }
    
    print(f"Fetching events from {start_date} to {end_date}...")
    try:
        response = requests.get(URL, params=params)
        print(f"Status Code: {response.status_code}")
        data = response.json()
        print("Response Body:", json.dumps(data, indent=2))
        
        if response.status_code == 200:
            print(f"Total events found: {len(data.get('economicCalendar', []))}")
            if data.get('economicCalendar'):
                print("\nFirst event sample:")
                print(json.dumps(data['economicCalendar'][0], indent=2))
        else:
            print(f"Request failed with status {response.status_code}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_finnhub()
