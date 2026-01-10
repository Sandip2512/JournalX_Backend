from app.mongo_database import db_client
from app.routes.users import get_community_members
from unittest.mock import MagicMock
import json

def debug_community():
    db_client.connect()
    db = db_client.db
    print(f"Total users in DB: {db.users.count_documents({})}")
    
    try:
        results = get_community_members(db)
        print(f"Success! Fetched {len(results)} members")
        print("Sample member:", results[0] if results else "None")
    except Exception as e:
        print(f"ERROR in get_community_members: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_community()
