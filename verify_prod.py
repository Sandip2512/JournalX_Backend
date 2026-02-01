import requests
import json

base_url = "https://journal-x-backend.vercel.app"

def check_endpoint(path):
    url = f"{base_url}{path}"
    print(f"Checking {url}...")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            if "version" in data:
                print(f"Version: {data['version']}")
            if "routes" in data:
                print(f"Found {len(data['routes'])} routes")
                sub_routes = [r for r in data['routes'] if "subscriptions" in r['path']]
                print(f"Subscription routes found: {json.dumps(sub_routes, indent=2)}")
            return data
    except Exception as e:
        print(f"Error: {e}")
    return None

print("--- HEALTH CHECK ---")
check_endpoint("/health")

print("\n--- ROUTES CHECK ---")
check_endpoint("/debug/routes")
