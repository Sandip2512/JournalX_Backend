from pymongo.database import Database
from datetime import datetime
from typing import List, Optional
import uuid
import logging

logger = logging.getLogger(__name__)


def create_post(db: Database, user_id: str, content: str, image_file_id: Optional[str] = None) -> dict:
    """Create a new post"""
    try:
        # Get user info for the post
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")
        
        post_id = str(uuid.uuid4())
        post_data = {
            "post_id": post_id,
            "user_id": user_id,
            "content": content,
            "image_file_id": image_file_id,
            "created_at": datetime.now(),
            "updated_at": None
        }
        
        db.posts.insert_one(post_data)
        logger.info(f"Created post {post_id} for user {user_id}")
        
        # Remove MongoDB _id to avoid serialization errors
        post_data.pop("_id", None)
        
        # Return post with user info
        return {
            **post_data,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get("email", ""),
            "like_count": 0,
            "comment_count": 0,
            "reactions": {},
            "user_reaction": None,
            "user_has_liked": False,
            "image_url": f"/api/posts/images/{image_file_id}" if image_file_id else None
        }
    except Exception as e:
        logger.error(f"Error creating post: {str(e)}")
        raise


def get_posts(db: Database, skip: int = 0, limit: int = 20) -> List[dict]:
    """Get paginated posts sorted by creation date (newest first) - Optimized"""
    try:
        # 1. Fetch raw posts
        posts = list(db.posts.find().sort("created_at", -1).skip(skip).limit(limit))
        if not posts:
            return []

        post_ids = [p["post_id"] for p in posts]
        user_ids = list(set(p["user_id"] for p in posts))

        # 2. Batch Fetch Users
        users_cursor = db.users.find({"user_id": {"$in": user_ids}})
        users_map = {u["user_id"]: u for u in users_cursor}

        # 3. Batch Fetch Reaction Counts
        # Format: { post_id: { emoji: count, ... } }
        reaction_pipeline = [
            {"$match": {"post_id": {"$in": post_ids}}},
            {"$group": {
                "_id": {"post_id": "$post_id", "emoji": "$emoji"},
                "count": {"$sum": 1}
            }}
        ]
        reactions_map = {}
        for r in db.post_likes.aggregate(reaction_pipeline):
            _id = r.get("_id", {})
            if not isinstance(_id, dict):
                continue
                
            pid = _id.get("post_id")
            emoji = _id.get("emoji") or "❤️"
            
            if pid:
                if pid not in reactions_map:
                    reactions_map[pid] = {}
                reactions_map[pid][emoji] = r.get("count", 0)

        # 4. Batch Fetch Comment Counts
        comment_pipeline = [
            {"$match": {"post_id": {"$in": post_ids}}},
            {"$group": {"_id": "$post_id", "count": {"$sum": 1}}}
        ]
        comments_map = {c["_id"]: c["count"] for c in db.post_comments.aggregate(comment_pipeline)}

        # 5. Enrich Posts
        enriched_posts = []
        for post in posts:
            user = users_map.get(post["user_id"])
            if not user:
                continue

            pid = post["post_id"]
            post_reactions = reactions_map.get(pid, {})
            # Calculate total like count from reactions
            like_count = sum(post_reactions.values())
            comment_count = comments_map.get(pid, 0)
            
            # Clean up for Pydantic
            post.pop("_id", None)
            
            enriched_posts.append({
                **post,
                "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Anonymous",
                "user_email": user.get("email", ""),
                "like_count": like_count,
                "comment_count": comment_count,
                "reactions": post_reactions,
                "user_reaction": None,
                "user_has_liked": False,
                "image_url": f"/api/posts/images/{str(post['image_file_id'])}" if post.get("image_file_id") else None
            })
        
        return enriched_posts
    except Exception as e:
        logger.error(f"Error getting posts: {str(e)}")
        raise


def get_post_by_id(db: Database, post_id: str) -> Optional[dict]:
    """Get a single post by ID"""
    try:
        post = db.posts.find_one({"post_id": post_id})
        if not post:
            return None
        
        user = db.users.find_one({"user_id": post["user_id"]})
        if not user:
            return None
        
        # Count likes and comments
        like_count = db.post_likes.count_documents({"post_id": post_id})
        comment_count = db.post_comments.count_documents({"post_id": post_id})
        
        return {
            **post,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get("email", ""),
            "like_count": like_count,
            "comment_count": comment_count,
            "reactions": get_reaction_counts(db, post_id),
            "image_url": f"/api/posts/images/{str(post['image_file_id'])}" if post.get("image_file_id") else None
        }
        # Clean for Pydantic
        result.pop("_id", None)
        return result
    except Exception as e:
        logger.error(f"Error getting post {post_id}: {str(e)}")
        raise


def update_post(db: Database, post_id: str, user_id: str, content: str) -> Optional[dict]:
    """Update a post (only by owner)"""
    try:
        post = db.posts.find_one({"post_id": post_id})
        if not post:
            return None
        
        if post["user_id"] != user_id:
            raise PermissionError("You can only update your own posts")
        
        db.posts.update_one(
            {"post_id": post_id},
            {"$set": {"content": content, "updated_at": datetime.now()}}
        )
        
        return get_post_by_id(db, post_id)
    except Exception as e:
        logger.error(f"Error updating post {post_id}: {str(e)}")
        raise


def delete_post(db: Database, post_id: str, user_id: str, is_admin: bool = False, is_moderator: bool = False) -> bool:
    """Delete a post (only by owner, admin, or moderator)"""
    try:
        post = db.posts.find_one({"post_id": post_id})
        if not post:
            return False
        
        if not (is_admin or is_moderator) and post["user_id"] != user_id:
            raise PermissionError("You can only delete your own posts")
        
        # Delete associated likes and comments
        db.post_likes.delete_many({"post_id": post_id})
        db.post_comments.delete_many({"post_id": post_id})
        
        # Delete the post
        result = db.posts.delete_one({"post_id": post_id})
        
        logger.info(f"Deleted post {post_id}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting post {post_id}: {str(e)}")
        raise



def get_reaction_counts(db: Database, post_id: str) -> dict:
    """Get counts of reactions per emoji"""
    pipeline = [
        {"$match": {"post_id": post_id}},
        {"$group": {"_id": "$emoji", "count": {"$sum": 1}}}
    ]
    results = list(db.post_likes.aggregate(pipeline))
    # Ensure keys are strings (never None) for Pydantic
    return {str(r["_id"] or "❤️"): r["count"] for r in results}


# ============= LIKES / REACTIONS =============

def toggle_reaction(db: Database, post_id: str, user_id: str, emoji: str = "❤️") -> dict:
    """Toggle a reaction (like) on a post"""
    try:
        # Check if post exists
        post = db.posts.find_one({"post_id": post_id})
        if not post:
            raise ValueError("Post not found")
        
        # Check if already reacted
        existing = db.post_likes.find_one({"post_id": post_id, "user_id": user_id})
        
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")
            
        user_name = f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()

        if existing:
            if existing.get("emoji") == emoji:
                # Same emoji -> Remove it (Toggle Off)
                db.post_likes.delete_one({"_id": existing["_id"]})
                logger.info(f"User {user_id} removed reaction {emoji} from post {post_id}")
                return {"action": "removed", "like_id": existing["like_id"]}
            else:
                # Different emoji -> Update it
                db.post_likes.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {"emoji": emoji, "created_at": datetime.now()}}
                )
                logger.info(f"User {user_id} changed reaction to {emoji} on post {post_id}")
                return {
                    "action": "updated",
                    "like_id": existing["like_id"],
                    "post_id": post_id,
                    "user_id": user_id, 
                    "user_name": user_name,
                    "emoji": emoji,
                    "created_at": datetime.now()
                }
        else:
            # New reaction
            like_id = str(uuid.uuid4())
            like_data = {
                "like_id": like_id,
                "post_id": post_id,
                "user_id": user_id,
                "emoji": emoji,
                "created_at": datetime.now()
            }
            db.post_likes.insert_one(like_data)
            logger.info(f"User {user_id} reacted {emoji} to post {post_id}")
            
            # Remove _id adding by insert_one to avoid serialization error
            like_data.pop("_id", None)
            
            return {
                "action": "added",
                **like_data,
                "user_name": user_name
            }

    except Exception as e:
        logger.error(f"Error toggling reaction: {str(e)}")
        raise


def remove_like(db: Database, post_id: str, user_id: str) -> bool:
    """Unlike a post"""
    try:
        result = db.post_likes.delete_one({"post_id": post_id, "user_id": user_id})
        logger.info(f"User {user_id} unliked post {post_id}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing like: {str(e)}")
        raise


def get_post_likes(db: Database, post_id: str) -> List[dict]:
    """Get all likes for a post"""
    try:
        likes = list(db.post_likes.find({"post_id": post_id}).sort("created_at", -1))
        
        # Enrich with user info
        enriched_likes = []
        for like in likes:
            user = db.users.find_one({"user_id": like["user_id"]})
            if user:
                enriched_likes.append({
                    **like,
                    "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
                })
        
        return enriched_likes
    except Exception as e:
        logger.error(f"Error getting likes for post {post_id}: {str(e)}")
        raise


def get_user_reaction(db: Database, post_id: str, user_id: str) -> Optional[str]:
    """Get the emoji user reacted with, if any"""
    try:
        like = db.post_likes.find_one({"post_id": post_id, "user_id": user_id})
        return like.get("emoji") if like else None
    except Exception as e:
        logger.error(f"Error checking reaction status: {str(e)}")
        raise


# ============= COMMENTS =============

def create_comment(db: Database, post_id: str, user_id: str, content: str, parent_id: Optional[str] = None) -> dict:
    """Add a comment to a post"""
    try:
        # Check if post exists
        post = db.posts.find_one({"post_id": post_id})
        if not post:
            raise ValueError("Post not found")
        
        # Get user info
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")
        
        comment_id = str(uuid.uuid4())
        comment_data = {
            "comment_id": comment_id,
            "post_id": post_id,
            "parent_id": parent_id,
            "user_id": user_id,
            "content": content,
            "created_at": datetime.now(),
            "updated_at": None
        }
        
        db.post_comments.insert_one(comment_data)
        logger.info(f"User {user_id} commented on post {post_id}")
        
        # Remove MongoDB _id
        comment_data.pop("_id", None)
        
        return {
            **comment_data,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            "user_email": user.get("email", ""),
            "like_count": 0,
            "user_has_liked": False
        }
    except Exception as e:
        logger.error(f"Error creating comment: {str(e)}")
        raise


def get_post_comments(db: Database, post_id: str) -> List[dict]:
    """Get all comments for a post"""
    try:
        comments = list(db.post_comments.find({"post_id": post_id}).sort("created_at", 1))
        
        # Enrich with user info and likes
        enriched_comments = []
        for comment in comments:
            user = db.users.find_one({"user_id": comment["user_id"]})
            
            # Count likes
            like_count = db.comment_likes.count_documents({"comment_id": comment["comment_id"]})
            
            if user:
                enriched_comments.append({
                    **comment,
                    "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
                    "user_email": user.get("email", ""),
                    "like_count": like_count
                })
        
        return enriched_comments
    except Exception as e:
        logger.error(f"Error getting comments for post {post_id}: {str(e)}")
        raise


def delete_comment(db: Database, comment_id: str, user_id: str, is_admin: bool = False, is_moderator: bool = False) -> bool:
    """Delete a comment (only by owner, admin, or moderator)"""
    try:
        comment = db.post_comments.find_one({"comment_id": comment_id})
        if not comment:
            return False
        
        if not (is_admin or is_moderator) and comment["user_id"] != user_id:
            raise PermissionError("You can only delete your own comments")
        
        result = db.post_comments.delete_one({"comment_id": comment_id})
        
        # Delete associated likes
        db.comment_likes.delete_many({"comment_id": comment_id})
        
        logger.info(f"Deleted comment {comment_id}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error deleting comment {comment_id}: {str(e)}")
        raise


def create_comment_like(db: Database, comment_id: str, user_id: str) -> dict:
    """Like a comment"""
    try:
        # Check if comment exists
        comment = db.post_comments.find_one({"comment_id": comment_id})
        if not comment:
            raise ValueError("Comment not found")
        
        # Check if already liked
        existing_like = db.comment_likes.find_one({"comment_id": comment_id, "user_id": user_id})
        if existing_like:
            raise ValueError("You already liked this comment")
        
        # Get user info
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise ValueError("User not found")
        
        like_id = str(uuid.uuid4())
        like_data = {
            "like_id": like_id,
            "comment_id": comment_id,
            "user_id": user_id,
            "created_at": datetime.now()
        }
        
        db.comment_likes.insert_one(like_data)
        logger.info(f"User {user_id} liked comment {comment_id}")
        
        return {
            **like_data,
            "user_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip()
        }
    except Exception as e:
        logger.error(f"Error creating comment like: {str(e)}")
        raise


def remove_comment_like(db: Database, comment_id: str, user_id: str) -> bool:
    """Unlike a comment"""
    try:
        result = db.comment_likes.delete_one({"comment_id": comment_id, "user_id": user_id})
        logger.info(f"User {user_id} unliked comment {comment_id}")
        return result.deleted_count > 0
    except Exception as e:
        logger.error(f"Error removing comment like: {str(e)}")
        raise


def check_user_liked_comment(db: Database, comment_id: str, user_id: str) -> bool:
    """Check if a user has liked a comment"""
    try:
        like = db.comment_likes.find_one({"comment_id": comment_id, "user_id": user_id})
        return like is not None
    except Exception as e:
        logger.error(f"Error checking comment like status: {str(e)}")
        raise
