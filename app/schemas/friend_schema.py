from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional, List

# Friend Request Models
class FriendRequestCreate(BaseModel):
    recipient_id: str

class FriendRequestResponse(BaseModel):
    request_id: str
    requester_id: str
    recipient_id: str
    status: str  # pending, accepted, rejected
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    # Extra details for UI
    requester_name: Optional[str] = None
    recipient_name: Optional[str] = None
    requester_username: Optional[str] = None
    recipient_username: Optional[str] = None

class FriendshipResponse(BaseModel):
    friendship_id: str
    user_id: str # The friend's ID (relative to the viewer)
    name: str
    username: Optional[str] = None
    connected_at: datetime
    status: str = "connected"
    last_seen: Optional[datetime] = None
    is_online: bool = False

class UserSearchResponse(BaseModel):
    user_id: str
    username: Optional[str] = None
    first_name: str
    last_name: str
    is_friend: bool = False
    has_pending_request: bool = False
    is_self: bool = False
