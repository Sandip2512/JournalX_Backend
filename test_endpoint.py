import requests
import sys

BASE_URL = "http://127.0.0.1:8000"

def check_endpoint(url):
    try:
        print(f"Checking {url}...")
        response = requests.get(url)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Response:", response.json())
            return True
        else:
            print("Error Response:", response.text)
            return False
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

print("=== Backend Health Check ===")
if check_endpoint(f"{BASE_URL}/health"):
    print("\n✅ Backend is UP")
else:
    print("\n❌ Backend seems DOWN or unhealthy")

print("\n=== Mistakes Endpoint Check ===")
if check_endpoint(f"{BASE_URL}/api/mistakes/analytics/1?time_filter=all"):
    print("\n✅ Mistakes Endpoint WORKED")
else:
    print("\n❌ Mistakes Endpoint FAILED")
