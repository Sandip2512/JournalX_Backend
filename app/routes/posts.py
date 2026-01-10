from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from pymongo.database import Database
from typing import List, Optional
import logging
from io import BytesIO

from app.mongo_database import get_db
from app.routes.auth import get_current_user
from app.schemas.post_schema import (
    PostCreate, PostResponse, PostUpdate,
    LikeResponse, CommentCreate, CommentResponse, CommentLikeResponse
)
from app.crud.post_crud import (
    create_post, get_posts, get_post_by_id, delete_post,
    toggle_reaction, remove_like, get_post_likes, get_user_reaction,
    create_comment, get_post_comments, delete_comment,
    create_comment_like, remove_comment_like, check_user_liked_comment
)
from app.services.image_storage_service import get_image_storage_service

logger = logging.getLogger(__name__)
router = APIRouter()


# ============= POSTS =============

@router.post("/", response_model=PostResponse)
async def create_new_post(
    content: str = Form(...),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Create a new post with optional image upload.
    Requires authentication.
    """
    try:
        logger.info(f"📝 User {current_user.get('email')} is creating a post: {content[:20]}...")
        image_file_id = None
        
        # Handle image upload if provided
        if image:
            # Validate file type
            if not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="File must be an image")
            
            # Validate file size (max 5MB)
            image_data = await image.read()
            if len(image_data) > 5 * 1024 * 1024:
                raise HTTPException(status_code=400, detail="Image size must be less than 5MB")
            
            # Upload to GridFS
            storage_service = get_image_storage_service(db)
            image_file_id = storage_service.upload_image(
                image_data,
                image.filename,
                image.content_type
            )
        
        # Create post
        post = create_post(db, current_user["user_id"], content, image_file_id)
        
        # Ensure image_url is consistently set and _id is removed
        if image_file_id:
             post["image_url"] = f"/api/posts/images/{str(image_file_id)}"
             post["image_file_id"] = str(image_file_id)
        
        # Final cleanup for Pydantic
        post.pop("_id", None)
        
        return PostResponse(**post)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating post: {str(e)}")


@router.get("/", response_model=List[PostResponse])
def get_post_feed(
    skip: int = 0,
    limit: int = 20,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get paginated feed of posts.
    Requires authentication.
    """
    try:
        if limit > 100:
            limit = 100  # Max limit
        
        posts = get_posts(db, skip, limit)
        
        # Add user's reaction status for each post
        for post in posts:
            reaction = get_user_reaction(db, post["post_id"], current_user["user_id"])
            post["user_reaction"] = reaction
            post["user_has_liked"] = bool(reaction)
        
        return [PostResponse(**post) for post in posts]
    except Exception as e:
        logger.error(f"Error getting posts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting posts: {str(e)}")


@router.get("/{post_id}", response_model=PostResponse)
def get_single_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get a single post by ID.
    Requires authentication.
    """
    try:
        post = get_post_by_id(db, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        reaction = get_user_reaction(db, post_id, current_user["user_id"])
        post["user_reaction"] = reaction
        post["user_has_liked"] = bool(reaction)
        return PostResponse(**post)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting post: {str(e)}")


@router.delete("/{post_id}")
def delete_existing_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Delete a post. Only the post owner, admin, or moderator can delete.
    Requires authentication.
    """
    try:
        is_admin = current_user.get("role") == "admin"
        is_moderator = current_user.get("role") == "moderator"
        success = delete_post(db, post_id, current_user["user_id"], is_admin, is_moderator)
        
        if not success:
            raise HTTPException(status_code=404, detail="Post not found")
        
        return {"message": "Post deleted successfully"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting post: {str(e)}")


# ============= LIKES =============

@router.post("/{post_id}/like", response_model=LikeResponse)
def like_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Like a post (Default Heart Reaction).
    Requires authentication.
    """
    try:
        result = toggle_reaction(db, post_id, current_user["user_id"], emoji="❤️")
        
        # If action was removed, we return a 200 with different body or handled by frontend?
        # PostResponse isn't expected here. LikeResponse is.
        # If removed, result has {"action": "removed", "like_id": ...}.
        # LikeResponse requires like_id, post_id, user_id, user_name, created_at
        
        if result["action"] == "removed":
             # Hack: Return dummy or handle in frontend. 
             # Better: return 204 or specific message.
             # Schema says LikeResponse. 
             # Let's return the like_id but with nulls? No, Pydantic validation.
             # Note: For legacy "toggle" via /like, frontend usually handles 200 OK.
             # If I return JSONResponse it bypasses response_model check? Yes.
             from fastapi.responses import JSONResponse
             return JSONResponse(content={"message": "Unliked", "action": "removed"})
        
        return LikeResponse(**result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error liking post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error liking post: {str(e)}")


class ReactionRequest(BaseModel):
    emoji: str


@router.post("/{post_id}/react", response_model=dict)
def react_to_post(
    post_id: str,
    reaction: ReactionRequest,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    React to a post with an emoji.
    Toggles if same emoji. Updates if different.
    """
    try:
        result = toggle_reaction(db, post_id, current_user["user_id"], emoji=reaction.emoji)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error reacting to post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error reacting to post: {str(e)}")


@router.delete("/{post_id}/like")
def unlike_post(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Unlike a post.
    Requires authentication.
    """
    try:
        success = remove_like(db, post_id, current_user["user_id"])
        if not success:
            raise HTTPException(status_code=404, detail="Like not found")
        
        return {"message": "Post unliked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unliking post: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error unliking post: {str(e)}")


@router.get("/{post_id}/likes", response_model=List[LikeResponse])
def get_likes(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get all likes for a post.
    Requires authentication.
    """
    try:
        likes = get_post_likes(db, post_id)
        return [LikeResponse(**like) for like in likes]
    except Exception as e:
        logger.error(f"Error getting likes: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting likes: {str(e)}")


# ============= COMMENTS =============

@router.post("/{post_id}/comments", response_model=CommentResponse)
def add_comment(
    post_id: str,
    comment_data: CommentCreate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Add a comment to a post.
    Requires authentication.
    """
    try:
        comment = create_comment(
            db, 
            post_id, 
            current_user["user_id"], 
            comment_data.content,
            comment_data.parent_id
        )
        return CommentResponse(**comment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error adding comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding comment: {str(e)}")


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
def get_comments(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get all comments for a post.
    Requires authentication.
    """
    try:
        comments = get_post_comments(db, post_id)
        
        # Add like status
        for comment in comments:
            comment["user_has_liked"] = check_user_liked_comment(db, comment["comment_id"], current_user["user_id"])
            
        return [CommentResponse(**comment) for comment in comments]
    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error getting comments: {str(e)}")


@router.delete("/{post_id}/comments/{comment_id}")
def delete_existing_comment(
    post_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Delete a comment. Only the comment owner, admin, or moderator can delete.
    Requires authentication.
    """
    try:
        is_admin = current_user.get("role") == "admin"
        is_moderator = current_user.get("role") == "moderator"
        success = delete_comment(db, comment_id, current_user["user_id"], is_admin, is_moderator)
        
        if not success:
            raise HTTPException(status_code=404, detail="Comment not found")
        
        return {"message": "Comment deleted successfully"}
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting comment: {str(e)}")


@router.post("/{post_id}/comments/{comment_id}/like", response_model=CommentLikeResponse)
def like_comment(
    post_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Like a comment.
    """
    try:
        like = create_comment_like(db, comment_id, current_user["user_id"])
        return CommentLikeResponse(**like)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error liking comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error liking comment: {str(e)}")


@router.delete("/{post_id}/comments/{comment_id}/like")
def unlike_comment(
    post_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Unlike a comment.
    """
    try:
        success = remove_comment_like(db, comment_id, current_user["user_id"])
        if not success:
            raise HTTPException(status_code=404, detail="Like not found")
        return {"message": "Comment unliked successfully"}
    except Exception as e:
        logger.error(f"Error unliking comment: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error unliking comment: {str(e)}")



# ============= IMAGES =============

@router.get("/images/{file_id}")
async def get_image(
    file_id: str,
    db: Database = Depends(get_db)
):
    """
    Retrieve an image from GridFS.
    Public endpoint (no authentication required for viewing images).
    """
    try:
        storage_service = get_image_storage_service(db)
        result = storage_service.get_image(file_id)
        
        if not result:
            raise HTTPException(status_code=404, detail="Image not found")
        
        image_data, content_type, filename = result
        
        return StreamingResponse(
            BytesIO(image_data),
            media_type=content_type,
            headers={"Content-Disposition": f"inline; filename={filename}"}
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving image: {str(e)}")
