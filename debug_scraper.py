import requests
from bs4 import BeautifulSoup

url = "https://www.forexfactory.com/calendar?day=today"
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
}

try:
    print(f"Fetching {url}...")
    response = requests.get(url, headers=headers, timeout=10)
    print(f"Status Code: {response.status_code}")
    
    with open("ff_debug.html", "w", encoding="utf-8") as f:
        f.write(response.text)
    print("Saved response to ff_debug.html")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    events = soup.select("tr.calendar_row")
    print(f"Found {len(events)} events in HTML.")
    
except Exception as e:
    print(f"Error: {e}")
