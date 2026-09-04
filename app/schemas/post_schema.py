from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime


class PostCreate(BaseModel):
    """Schema for creating a new post"""
    content: str = Field(..., min_length=1, max_length=5000, description="Post content")
    image_file_id: Optional[str] = Field(None, description="GridFS file ID for uploaded image")


class PostUpdate(BaseModel):
    """Schema for updating a post"""
    content: str = Field(..., min_length=1, max_length=5000, description="Updated post content")


class PostResponse(BaseModel):
    """Schema for post response"""
    post_id: str
    user_id: str
    user_name: str = Field(..., description="Full name of the user who created the post")
    user_email: str
    content: str
    image_file_id: Optional[str] = None
    image_url: Optional[str] = None
    like_count: int = 0
    reactions: Dict[str, int] = {}
    user_reaction: Optional[str] = None
    user_has_liked: bool = False
    comment_count: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class LikeCreate(BaseModel):
    """Schema for creating a like/reaction"""
    post_id: str
    user_id: str
    emoji: str = "❤️"


class LikeResponse(BaseModel):
    """Schema for like response"""
    like_id: str
    post_id: str
    user_id: str
    user_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    """Schema for creating a comment"""
    content: str = Field(..., min_length=1, max_length=1000, description="Comment content")
    parent_id: Optional[str] = Field(None, description="ID of parent comment if this is a reply")


class CommentUpdate(BaseModel):
    """Schema for updating a comment"""
    content: str = Field(..., min_length=1, max_length=1000, description="Updated comment content")


class CommentResponse(BaseModel):
    """Schema for comment response"""
    comment_id: str
    post_id: str
    parent_id: Optional[str] = None
    user_id: str
    user_name: str
    user_email: str
    content: str
    like_count: int = 0
    user_has_liked: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class CommentLikeResponse(BaseModel):
    """Schema for comment like response"""
    like_id: str
    comment_id: str
    user_id: str
    user_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True
