from pymongo.database import Database
from datetime import datetime
from typing import Optional, Dict, Any
from app.schemas.preferences_schema import PreferencesCreate, PreferencesUpdate

COLLECTION_NAME = "preferences"

def get_preferences(db: Database, user_id: str) -> Optional[Dict[str, Any]]:
    return db[COLLECTION_NAME].find_one({"user_id": user_id}, {"_id": 0})

def create_or_update_preferences(db: Database, user_id: str, prefs: PreferencesCreate | PreferencesUpdate) -> Dict[str, Any]:
    prefs_data = prefs.model_dump(exclude_unset=True)
    prefs_data["updated_at"] = datetime.utcnow().isoformat()
    
    db[COLLECTION_NAME].update_one(
        {"user_id": user_id},
        {"$set": prefs_data},
        upsert=True
    )
    
    return get_preferences(db, user_id)
