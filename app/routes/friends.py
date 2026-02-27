from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from typing import List
from bson.objectid import ObjectId
from datetime import datetime

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
    meeting_id: str = None

class MeetingResponse(BaseModel):
    user_id: str
    action: str # "admit" or "deny"

@router.post("/invite-room")
async def invite_to_room(
    invite: InviteRequest, 
    current_user = Depends(get_current_user), 
    db: Database = Depends(get_db)
):
    """Invite a friend to the trader room with meeting tracking"""
    meeting_id = invite.meeting_id or str(ObjectId())
    
    # Create or Update meeting record
    # Note: Using update_one with upsert=True to allow multiple "invitations" for the same meeting_id
    # but we store them as individual documents for simplicity of the current "status" checking logic.
    # However, if it's a new friend for an existing meeting, we just insert a new record for that pair.
    
    db.meetings.insert_one({
        "_id": ObjectId() if invite.meeting_id else ObjectId(meeting_id),
        "meeting_id": meeting_id, # Added generic meeting_id field for multi-participant lookup
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

@router.post("/meeting/create")
async def create_instant_meeting(current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Create an instant meeting session as Host"""
    meeting_id = str(ObjectId())
    # Create an initial record where the host is joined
    db.meetings.insert_one({
        "meeting_id": meeting_id,
        "host_id": current_user["user_id"],
        "invitee_id": current_user["user_id"], # Join self as host
        "status": "accepted",
        "created_at": datetime.utcnow(),
        "is_instant": True
    })
    return {"meeting_id": meeting_id, "host_id": current_user["user_id"]}

@router.post("/meeting/{meeting_id}/knock")
async def knock_for_admission(meeting_id: str, current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Request entry into a gated room"""
    # Check if a record already exists
    existing = db.meetings.find_one({
        "meeting_id": meeting_id,
        "invitee_id": current_user["user_id"]
    })
    
    if existing:
        if existing["status"] == "accepted":
            return {"status": "accepted", "message": "Already admitted"}
        return {"status": existing["status"], "message": "Request exists"}

    # Find the host of this room
    first_meeting = db.meetings.find_one({"meeting_id": meeting_id})
    if not first_meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    db.meetings.insert_one({
        "meeting_id": meeting_id,
        "host_id": first_meeting["host_id"],
        "invitee_id": current_user["user_id"],
        "status": "pending_admission",
        "created_at": datetime.utcnow()
    })
    
    return {"status": "pending_admission", "message": "Admission requested"}

@router.post("/meeting/{meeting_id}/respond")
async def respond_to_admission(meeting_id: str, response: MeetingResponse, current_user = Depends(get_current_user), db: Database = Depends(get_db)):
    """Host admits or denies a user"""
    # Verify current user is the host
    meeting_rec = db.meetings.find_one({
        "meeting_id": meeting_id,
        "host_id": current_user["user_id"]
    })
    
    if not meeting_rec:
        raise HTTPException(status_code=403, detail="Not authorized to admit users")
        
    new_status = "accepted" if response.action == "admit" else "denied"
    
    result = db.meetings.update_one(
        {"meeting_id": meeting_id, "invitee_id": response.user_id},
        {"$set": {"status": new_status, "responded_at": datetime.utcnow()}}
    )
    
    return {"status": new_status, "modified_count": result.modified_count}

@router.get("/meeting/{meeting_id}")
async def get_meeting_status(meeting_id: str, db: Database = Depends(get_db), current_user = Depends(get_current_user)):
    """Check meeting status - resolve unified meeting_id and aggregate status"""
    try:
        # Resolve unified ID first
        unified_id = meeting_id
        if len(meeting_id) == 24:
            m = db.meetings.find_one({"_id": ObjectId(meeting_id)})
            if m and m.get("meeting_id"):
                unified_id = m["meeting_id"]

        # Aggregate status: If any invitee has accepted this unified_id, return accepted.
        # This is CRITICAL for the Host when they invite multiple people.
        meetings = list(db.meetings.find({
            "meeting_id": unified_id,
            "$or": [
                {"host_id": current_user["user_id"]},
                {"invitee_id": current_user["user_id"]}
            ]
        }))
        
        if not meetings:
            return {"status": "not_found"}
            
        # If any record is accepted, the whole session is "active"
        is_accepted = any(m.get("status") == "accepted" for m in meetings)
        primary_meeting = meetings[0] # Use first record as metadata source
        
        # New: If host, return list of "knocking" users
        knocking_users = []
        if primary_meeting["host_id"] == current_user["user_id"]:
            all_meetings = list(db.meetings.find({"meeting_id": unified_id, "status": "pending_admission"}))
            for m in all_meetings:
                user = db.users.find_one({"user_id": m["invitee_id"]})
                if user:
                    knocking_users.append({
                        "user_id": m["invitee_id"],
                        "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                    })

        return {
            "id": unified_id,
            "status": "accepted" if is_accepted else primary_meeting["status"],
            "host_id": primary_meeting["host_id"],
            "invitee_id": primary_meeting["invitee_id"],
            "knocking_users": knocking_users
        }
    except Exception as e:
        print(f"Error in get_meeting_status: {e}")
        return {"status": "error"}

@router.get("/meeting/{meeting_id}/participants")
async def get_meeting_participants(meeting_id: str, db: Database = Depends(get_db)):
    """Get all participants who have joined this meeting session"""
    try:
        # Resolve unified ID first
        unified_id = meeting_id
        if len(meeting_id) == 24:
            m = db.meetings.find_one({"_id": ObjectId(meeting_id)})
            if m and m.get("meeting_id"):
                unified_id = m["meeting_id"]

        # Find all meeting records for this unified ID
        meetings = list(db.meetings.find({"meeting_id": unified_id}))
        
        if not meetings:
            return []
            
        # Collect all unique user IDs (hosts and invitees who accepted)
        participant_ids = set()
        for m in meetings:
            participant_ids.add(m["host_id"])
            if m["status"] == "accepted":
                participant_ids.add(m["invitee_id"])
        
        print(f"[Mesh] Resolved Room {unified_id}. Found {len(participant_ids)} participants.")
                
        # Fetch user info for each ID
        participants = []
        for uid in participant_ids:
            user = db.users.find_one({"user_id": uid})
            if user:
                participants.append({
                    "user_id": uid,
                    "first_name": user.get("first_name", "Trader"),
                    "last_name": user.get("last_name", ""),
                    "avatar_url": user.get("avatar_url", ""),
                    "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                })
        
        return {
            "meeting_id": unified_id,
            "participants": participants
        }
    except Exception as e:
        print(f"Error in get_meeting_participants: {e}")
        return {"meeting_id": meeting_id, "participants": [], "error": str(e)}

@router.post("/meeting/{meeting_id}/accept")
async def accept_meeting(meeting_id: str, db: Database = Depends(get_db), current_user = Depends(get_current_user)):
    """Accept/Start the meeting for the current user"""
    try:
        # Update by meeting_id and invitee_id to be specific
        db.meetings.update_one(
            {"meeting_id": meeting_id, "invitee_id": current_user["user_id"]},
            {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
        )
        # Fallback for old _id based invites
        if len(meeting_id) == 24:
            db.meetings.update_one(
                {"_id": ObjectId(meeting_id), "invitee_id": current_user["user_id"]},
                {"$set": {"status": "accepted", "accepted_at": datetime.utcnow()}}
            )
        return {"message": "Meeting accepted"}
    except:
        return {"message": "Error"}
