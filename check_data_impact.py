from pymongo import MongoClient
import os
from dotenv import load_dotenv

load_dotenv()

mongo_uri = os.getenv("MONGO_URI") or "mongodb://localhost:27017/"
client = MongoClient(mongo_uri)

db_name = os.getenv("DB_NAME", "JournalX")
# Ensure correct DB
if db_name not in client.list_database_names():
    for name in client.list_database_names():
        if "journal" in name.lower():
            db_name = name
            break
            
db = client[db_name]
print(f"Using database: {db_name}")

# Check impact levels
events = list(db.economic_events.find({}, {"impact_level": 1, "status": 1, "event_name": 1}))
print(f"Total events: {len(events)}")
for e in events:
    print(e)
