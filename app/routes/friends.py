from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from typing import List

from app.mongo_database import get_db
# Import get_current_user from auth.py. 
# Since we didn't export it explicitly in __init__, we import from module.
from app.routes.auth import get_current_user
from app.schemas.friend_schema import FriendRequestCreate, FriendRequestResponse, FriendshipResponse, UserSearchResponse
from app.crud.friend_crud import (
    send_friend_request, 
    get_pending_requests, 
    accept_friend_request, 
    reject_friend_request,
    get_friends, 
    search_users_for_friendship
)

router = APIRouter()

@router.get("", response_model=List[FriendshipResponse])
async def get_friends_list(current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """List all friends"""
    return get_friends(db, current_user["user_id"])

@router.get("/requests", response_model=List[FriendRequestResponse])
async def get_requests(current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """List pending friend requests received"""
    return get_pending_requests(db, current_user["user_id"])

@router.post("/request", response_model=FriendRequestResponse)
async def create_request(request: FriendRequestCreate, current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Send a friend request"""
    if request.recipient_id == current_user["user_id"]:
        raise HTTPException(status_code=400, detail="Cannot friend yourself")
    
    result = send_friend_request(db, current_user["user_id"], request.recipient_id)
    if not result:
        raise HTTPException(status_code=404, detail="User not found")
    
    # If returned a dict with status=already_friends
    if result.get("status") == "already_friends":
         raise HTTPException(status_code=400, detail="Already friends")
         
    return result

@router.post("/accept/{request_id}")
async def accept_request(request_id: str, current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Accept a friend request"""
    result = accept_friend_request(db, request_id, current_user["user_id"])
    if not result:
        raise HTTPException(status_code=400, detail="Request not found or invalid")
    return {"message": "Friend request accepted"}

@router.post("/reject/{request_id}")
async def reject_request(request_id: str, current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Reject a friend request"""
    result = reject_friend_request(db, request_id, current_user["user_id"])
    if not result:
        raise HTTPException(status_code=400, detail="Request not found")
    return {"message": "Friend request rejected"}

@router.get("/search", response_model=List[UserSearchResponse])
async def search_people(query: str = Query(..., min_length=2), current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Search for people to friend"""
    return search_users_for_friendship(db, query, current_user["user_id"])

from pydantic import BaseModel
from datetime import datetime
from bson import ObjectId

class InviteRequest(BaseModel):
    recipient_id: str

@router.post("/invite-room")
async def invite_to_room(
    invite: InviteRequest, 
    current_user = Depends(get_current_user), 
    db: Database = Depends(get_db)
):
    """Invite a friend to the trader room with meeting tracking"""
    meeting_id = str(ObjectId())
    
    # Create meeting record
    db.meetings.insert_one({
        "_id": ObjectId(meeting_id),
        "host_id": current_user["user_id"],
        "invitee_id": invite.recipient_id,
        "status": "pending",
        "created_at": datetime.utcnow()
    })

    # Create notification
    notification = {
        "user_id": invite.recipient_id,
        "title": "Room Invitation",
        "content": f"{current_user.get('first_name', 'A friend')} invited you to a Trade Room.",
        "type": "room_invite",
        "created_at": datetime.utcnow(),
        "is_read": False,
        "metadata": {
            "action_url": f"/trader-room?meetingId={meeting_id}",
            "action_label": "Join Room",
            "inviter_id": current_user["user_id"],
            "meeting_id": meeting_id
        }
    }
    db.notifications.insert_one(notification)
    return {"message": "Invite sent", "meeting_id": meeting_id}

@router.get("/meeting/{meeting_id}")
async def get_meeting_status(meeting_id: str, db: Database = Depends(get_db)):
    """Check meeting status"""
    try:
        meeting = db.meetings.find_one({"_id": ObjectId(meeting_id)})
        if not meeting:
            return {"status": "not_found"}
        return {
            "id": meeting_id,
            "status": meeting["status"],
            "host_id": meeting["host_id"],
            "invitee_id": meeting["invitee_id"]
        }
    except:
        return {"status": "error"}

@router.post("/meeting/{meeting_id}/accept")
async def accept_meeting(meeting_id: str, db: Database = Depends(get_db), current_user = Depends(get_current_user)):
    """Accept/Start the meeting"""
    try:
        db.meetings.update_one(
            {"_id": ObjectId(meeting_id)},
            {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
        )
        return {"message": "Meeting accepted"}
    except:
        return {"message": "Error"}
