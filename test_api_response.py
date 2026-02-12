import requests
import json

URL = "http://localhost:8000/api/calendar/events"
USER_ID = "test_user" # We need to check if authentication is required or what user_id to use

def test_api():
    params = {
        "user_id": USER_ID,
        "start_date": "2026-02-01",
        "end_date": "2026-02-28",
        "timezone_offset": 5.5
    }
    
    print(f"Testing API: {URL} with params {params}")
    try:
        response = requests.get(URL, params=params)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                events = data.get("events", [])
                print(f"Total events returned: {len(events)}")
                if events:
                    print("First event sample:")
                    print(json.dumps(events[0], indent=2))
            else:
                print("API returned success: False")
        else:
            print("Error response:", response.text)
            
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_api()
