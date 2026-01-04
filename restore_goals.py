from app.mongo_database import get_db
from datetime import datetime

def restore_goals():
    db = get_db()
    # Reactivate all goals that were recently marked as achieved but deactivated
    result = db.goals.update_many(
        {"is_active": False, "achieved": True},
        {"$set": {"is_active": True}}
    )
    print(f"Goal Restoration Complete: {result.modified_count} goals reactivated.")

if __name__ == "__main__":
    restore_goals()
