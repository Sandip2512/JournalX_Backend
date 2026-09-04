from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class NotificationBase(BaseModel):
    id: str
    title: str
    content: str
    created_at: datetime
    type: str # 'announcement' or 'personal'
    is_read: bool = False

class NotificationList(BaseModel):
    notifications: List[NotificationBase]
    unread_count: int
