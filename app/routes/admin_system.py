from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo.database import Database
from typing import List, Optional
from datetime import datetime, timedelta
from app.mongo_database import get_db
from app.routes.admin import get_current_user_role
from pydantic import BaseModel

router = APIRouter()

# --- Schemas ---
class AnnouncementCreate(BaseModel):
    title: str
    content: str

class AnnouncementUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    is_active: Optional[bool] = None

# --- Endpoints ---

@router.get("/stats")
def get_dashboard_stats(
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    total_users = db.users.count_documents({})
    total_trades = db.trades.count_documents({})
    active_users = db.users.count_documents({"is_active": True})
    
    # Calculate some activity metrics
    one_day_ago = datetime.utcnow() - timedelta(days=1)
    new_users_24h = db.users.count_documents({"created_at": {"$gte": one_day_ago}})
    trades_24h = db.trades.count_documents({"close_time": {"$gte": one_day_ago}})
    
    return {
        "total_users": total_users,
        "total_trades": total_trades,
        "active_users": active_users,
        "new_users_24h": new_users_24h,
        "trades_24h": trades_24h
    }

@router.get("/logs/login")
def get_login_logs(
    skip: int = 0, 
    limit: int = 50,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    logs = list(db.login_history.find().sort("timestamp", -1).skip(skip).limit(limit))
    
    result = []
    for log in logs:
        user_email = "Unknown"
        user = db.users.find_one({"user_id": log.get("user_id")})
        if user:
            user_email = user.get("email")
            
        result.append({
            "id": str(log.get("_id")),
            "user_id": log.get("user_id"),
            "email": user_email,
            "ip_address": log.get("ip_address"),
            "status": log.get("status"),
            "timestamp": log.get("timestamp")
        })
        
    return result

@router.post("/announcements")
def create_announcement(
    announcement: AnnouncementCreate,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    new_announcement = {
        "title": announcement.title,
        "content": announcement.content,
        "is_active": True,
        "created_at": datetime.utcnow()
    }
    result = db.announcements.insert_one(new_announcement)
    new_announcement["id"] = str(result.inserted_id)
    new_announcement.pop("_id", None)
    return new_announcement

@router.get("/announcements")
def get_announcements(
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Auto-delete announcements older than 24 hours
    twenty_four_hours_ago = datetime.utcnow() - timedelta(hours=24)
    db.announcements.delete_many({"created_at": {"$lt": twenty_four_hours_ago}})
    
    # Return all remaining announcements
    announcements = list(db.announcements.find().sort("created_at", -1))
    for a in announcements:
        a["id"] = str(a.pop("_id"))
    return announcements

@router.delete("/announcements/{announcement_id}")
def delete_announcement(
    announcement_id: str,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    import bson
    try:
        oid = bson.ObjectId(announcement_id)
        result = db.announcements.delete_one({"_id": oid})
    except:
        # Fallback if ID is stored as string or invalid
         result = db.announcements.delete_one({"_id": announcement_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Announcement not found")
    
    return {"message": "Announcement deleted successfully"}
