from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

# Connect to MongoDB
mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)

print("Databases:", client.list_database_names())

db_name = os.getenv("DB_NAME", "JournalX")
print(f"Checking database: {db_name}")

if db_name not in client.list_database_names():
    print(f"Database {db_name} does not exist!")
    # Try finding a likely candidate
    for name in client.list_database_names():
        if "journal" in name.lower():
            db_name = name
            print(f"Switching to {db_name}")
            break

db = client[db_name]

# Check events
try:
    count = db.economic_events.count_documents({})
    print(f"Total events in {db_name}: {count}")

    if count > 0:
        print("Sample event:")
        print(db.economic_events.find_one())
    else:
        print("No events found. The scraper might not have run yet.")
except Exception as e:
    print(f"Error checking database: {e}")
