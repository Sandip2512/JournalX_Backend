from fastapi import APIRouter, Depends
from pymongo.database import Database
from app.mongo_database import get_db
from app.routes.auth import get_current_user

router = APIRouter()

@router.get("/active")
def get_active_announcements(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user) 
):
    # Only return the most recent active announcement for the banner
    announcement = db.announcements.find_one(
        {"is_active": True},
        sort=[("created_at", -1)]
    )
        
    if not announcement:
        return None

    announcement["id"] = str(announcement.pop("_id"))
    return announcement
