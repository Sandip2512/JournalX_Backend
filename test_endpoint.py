import requests
import json

base_url = "http://localhost:8000"
user_id = "e5a933cf-d99e-4b85-8f6a-12e0f40d9b1a"

print("Fetching stats...")
r1 = requests.get(f"{base_url}/trades/stats/user/{user_id}")
print("Stats status:", r1.status_code)
# print(r1.text)

print("\nFetching trades...")
r2 = requests.get(f"{base_url}/trades/user/{user_id}?limit=10")
print("Trades status:", r2.status_code)
if r2.status_code != 200:
    print(r2.text)
else:
    print(f"Returned {len(r2.json())} trades")
    if len(r2.json()) > 0:
        print("First trade:", list(r2.json()[0].keys()))

