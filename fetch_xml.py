import requests

url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
try:
    response = requests.get(url)
    with open("ff_feed.xml", "wb") as f:
        f.write(response.content)
    print("Saved XML feed to ff_feed.xml")
except Exception as e:
    print(f"Error: {e}")
