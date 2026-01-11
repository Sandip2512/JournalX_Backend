from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.mongo_database import get_db
from app.routes.auth import get_current_user
from typing import List
from datetime import datetime, timedelta
import bson

router = APIRouter()

@router.get("/")
def get_notifications(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    
    # 1. Fetch active global announcements
    # Filter out announcements dismissed by this user
    dismissed_ids = [d["notification_id"] for d in db.notification_dismissals.find({"user_id": user_id})]
    
    # Create list of both ObjectId and string versions for robust filtering
    dismiss_filters = []
    for d_id in dismissed_ids:
        dismiss_filters.append(d_id)
        if bson.ObjectId.is_valid(d_id):
            dismiss_filters.append(bson.ObjectId(d_id))

    announcements = list(db.announcements.find({
        "is_active": True,
        "_id": {"$nin": dismiss_filters}
    }).sort("created_at", -1))
    
    # 2. Fetch user-specific notifications
    # Filter out dismissed personal notifications
    personal_notifications = list(db.notifications.find({
        "user_id": user_id,
        "is_dismissed": {"$ne": True}
    }).sort("created_at", -1))
    
    # Combine and format
    combined = []
    
    for a in announcements:
        combined.append({
            "id": str(a.get("_id")),
            "title": a.get("title", "Announcement"),
            "content": a.get("content", ""),
            "created_at": a.get("created_at"),
            "type": "announcement",
            "is_read": False 
        })
        
    for p in personal_notifications:
        combined.append({
            "id": str(p.get("_id")),
            "title": p.get("title", "Notification"),
            "content": p.get("content", ""),
            "created_at": p.get("created_at"),
            "type": "personal",
            "is_read": p.get("is_read", False)
        })
    
    # Sort combined by created_at desc
    combined.sort(key=lambda x: x["created_at"] or datetime.min, reverse=True)
    
    # Calculate unread count
    unread_count = sum(1 for n in combined if not n.get("is_read", False))
    
    return {
        "notifications": combined,
        "unread_count": unread_count
    }

@router.put("/dismiss-all")
def dismiss_all_notifications(
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    
    # 1. Dismiss all personal notifications
    db.notifications.update_many(
        {"user_id": user_id, "is_dismissed": {"$ne": True}},
        {"$set": {"is_dismissed": True, "is_read": True}}
    )
    
    # 2. Dismiss all currently active announcements for this user
    active_announcements = db.announcements.find({"is_active": True})
    for a in active_announcements:
        db.notification_dismissals.update_one(
            {"user_id": user_id, "notification_id": str(a["_id"])},
            {"$set": {"dismissed_at": datetime.now()}},
            upsert=True
        )
        
    return {"message": "All notifications dismissed"}

@router.put("/{notification_id}/dismiss")
def dismiss_notification(
    notification_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    user_id = current_user["user_id"]
    
    # Check if it's a personal notification first
    try:
        oid = bson.ObjectId(notification_id)
        result = db.notifications.update_one(
            {"_id": oid, "user_id": user_id},
            {"$set": {"is_dismissed": True}}
        )
    except:
        result = db.notifications.update_one(
            {"_id": notification_id, "user_id": user_id},
            {"$set": {"is_dismissed": True}}
        )
        
    if result.matched_count == 0:
        # If not personal, treat as announcement dismissal
        db.notification_dismissals.update_one(
            {"user_id": user_id, "notification_id": notification_id},
            {"$set": {"dismissed_at": datetime.now()}},
            upsert=True
        )
        
    return {"message": "Notification dismissed"}

@router.put("/{notification_id}/read")
def mark_notification_as_read(
    notification_id: str,
    db: Database = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    try:
        oid = bson.ObjectId(notification_id)
        result = db.notifications.update_one(
            {"_id": oid, "user_id": current_user["user_id"]},
            {"$set": {"is_read": True}}
        )
    except:
        # Fallback if stored as string
        result = db.notifications.update_one(
            {"_id": notification_id, "user_id": current_user["user_id"]},
            {"$set": {"is_read": True}}
        )
        
    if result.matched_count == 0:
        # If not found in personal, check if it's an announcement (though announcements don't have read state in DB normally)
        # For now, we only support marking personal ones as read.
        raise HTTPException(status_code=404, detail="Personal notification not found")
        
    return {"message": "Notification marked as read"}

