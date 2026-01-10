from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body, Request
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
    request: Request,
    content: str = Form(""),
    image: Optional[UploadFile] = File(None),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Create a new post with optional image upload.
    Requires authentication.
    """
    try:
        # Diagnostic logging
        token = request.headers.get("Authorization")
        content_type = request.headers.get("Content-Type")
        logger.info(f"📝 POST /api/posts/ | Content-Type: {content_type} | Token present: {bool(token)}")
        
        try:
            form = await request.form()
            logger.info(f"📝 Form keys received: {list(form.keys())}")
            if "content" in form:
                logger.info(f"📝 Content found in form, length: {len(form['content'])}")
        except Exception as fe:
            logger.error(f"❌ Error reading raw form: {fe}")

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
        logger.info(f"📋 Fetching feed [v2.1] | user: {current_user.get('email')} | skip: {skip} | limit: {limit}")
        # Use keyword arguments for robustness
        posts = get_posts(db=db, current_user_id=current_user["user_id"], skip=skip, limit=limit)
        return posts
    except Exception as e:
        logger.error(f"Error getting feed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching post feed")
        logger.error(f"Error getting feed: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching post feed")


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
        
        # Add user reaction info
        user_reaction = get_user_reaction(db, post_id, current_user["user_id"])
        post["user_reaction"] = user_reaction
        post["user_has_liked"] = user_reaction is not None
        
        return post
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching post")


@router.put("/{post_id}", response_model=PostResponse)
def update_existing_post(
    post_id: str,
    update_data: PostUpdate,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Update a post. Only the owner can update.
    Requires authentication.
    """
    try:
        logger.info(f"🔄 PUT /api/posts/{post_id} | user: {current_user.get('email')} | content_len: {len(update_data.content)}")
        updated_post = update_post(db, post_id, current_user["user_id"], update_data.content)
        if not updated_post:
            logger.warning(f"⚠️ Post not found or unauthorized for update: {post_id}")
            raise HTTPException(status_code=404, detail="Post not found or unauthorized")
        
        # Clean for Pydantic
        updated_post.pop("_id", None)
        logger.info(f"✅ Post updated successfully: {post_id}")
        return PostResponse(**updated_post)
    except PermissionError as pe:
        raise HTTPException(status_code=403, detail=str(pe))
    except Exception as e:
        logger.error(f"Error updating post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error updating post")


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
        post = get_post_by_id(db, post_id)
        if not post:
            raise HTTPException(status_code=404, detail="Post not found")
        
        # Check permissions: owner, admin, or moderator
        is_owner = post["user_id"] == current_user["user_id"]
        is_admin = current_user.get("role") == "admin"
        is_moderator = current_user.get("role") == "moderator"
        
        if not (is_owner or is_admin or is_moderator):
            raise HTTPException(status_code=403, detail="Not authorized to delete this post")
            
        success = delete_post(
            db, 
            post_id, 
            user_id=current_user["user_id"], 
            is_admin=is_admin, 
            is_moderator=is_moderator
        )
        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete post")
            
        return {"message": "Post deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting post")


# ============= LIKES =============

@router.post("/{post_id}/like", response_model=LikeResponse)
def like_post_endpoint(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Like a post (Default Heart Reaction).
    Requires authentication.
    """
    try:
        # Toggle reaction with default ❤️
        result = toggle_reaction(db, post_id, current_user["user_id"], "❤️")
        
        if not result:
            # If it was unliked (removed), return a success message or handle accordingly
            # But the response_model expects LikeResponse. 
            # Usually, toggle_reaction should return the new like or None.
            # Let's assume it returns the like document if added.
            raise HTTPException(status_code=200, detail="Post unliked")
            
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error liking post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error liking post")


class ReactionRequest(BaseModel):
    emoji: str


@router.post("/{post_id}/react")
def react_to_post_endpoint(
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
        result = toggle_reaction(db, post_id, current_user["user_id"], reaction.emoji)
        return {"success": True, "action": "added" if result else "removed"}
    except Exception as e:
        logger.error(f"Error reacting to post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error reacting to post")


@router.delete("/{post_id}/like")
def unlike_post_endpoint(
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
        return {"message": "Unliked successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error unliking post: {str(e)}")
        raise HTTPException(status_code=500, detail="Error unliking post")


@router.get("/{post_id}/likes", response_model=List[LikeResponse])
def get_likes_endpoint(
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
        return likes
    except Exception as e:
        logger.error(f"Error getting likes: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching likes")


# ============= COMMENTS =============

@router.post("/{post_id}/comments", response_model=CommentResponse)
def add_comment_endpoint(
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
        return comment
    except Exception as e:
        logger.error(f"Error adding comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error adding comment")


@router.get("/{post_id}/comments", response_model=List[CommentResponse])
def get_comments_endpoint(
    post_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Get all comments for a post.
    Requires authentication.
    """
    try:
        comments = get_post_comments(db, post_id, current_user["user_id"])
        return comments
    except Exception as e:
        logger.error(f"Error getting comments: {str(e)}")
        raise HTTPException(status_code=500, detail="Error fetching comments")


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
        # Permission check
        is_admin = current_user.get("role") == "admin"
        is_moderator = current_user.get("role") == "moderator"
        
        success = delete_comment(
            db, 
            comment_id, 
            user_id=current_user["user_id"], 
            is_admin=is_admin, 
            is_moderator=is_moderator
        )
        if not success:
            raise HTTPException(status_code=403, detail="Not authorized or comment not found")
        return {"message": "Comment deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error deleting comment")


@router.post("/{post_id}/comments/{comment_id}/like")
def like_comment_endpoint(
    post_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Like a comment.
    """
    try:
        create_comment_like(db, comment_id, current_user["user_id"])
        return {"success": True}
    except Exception as e:
        logger.error(f"Error liking comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error liking comment")


@router.delete("/{post_id}/comments/{comment_id}/like")
def unlike_comment_endpoint(
    post_id: str,
    comment_id: str,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Unlike a comment.
    """
    try:
        remove_comment_like(db, comment_id, current_user["user_id"])
        return {"success": True}
    except Exception as e:
        logger.error(f"Error unliking comment: {str(e)}")
        raise HTTPException(status_code=500, detail="Error unliking comment")


# ============= IMAGES =============

@router.get("/images/{file_id}")
def get_image_endpoint(
    file_id: str,
    db: Database = Depends(get_db)
):
    """
    Retrieve an image from GridFS.
    Public endpoint (no authentication required for viewing images).
    """
    try:
        storage_service = get_image_storage_service(db)
        image_data = storage_service.get_image(file_id)
        
        if not image_data:
            raise HTTPException(status_code=404, detail="Image not found")
            
        data, content_type, filename = image_data
        return StreamingResponse(BytesIO(data), media_type=content_type)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving image: {str(e)}")
        raise HTTPException(status_code=500, detail="Error retrieving image")
