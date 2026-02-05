import os
import requests
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("❌ Error: GEMINI_API_KEY not found.")
    exit(1)

# Try to list models
url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
print(f"📡 Requesting: {url}")

try:
    response = requests.get(url)
    print(f"📊 Status Code: {response.status_code}")
    if response.status_code == 200:
        models = response.json()
        print("✅ Models available:")
        with open("models_list.txt", "w", encoding="utf-8") as f:
            for m in models.get("models", []):
                line = f"- {m['name']}\n"
                print(line.strip())
                f.write(line)
    else:
        print(f"❌ Error Response: {response.text}")
except Exception as e:
    print(f"❌ Exception: {e}")
