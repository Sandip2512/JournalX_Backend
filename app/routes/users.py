from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
import logging
from app.mongo_database import get_db
from app.crud.user_crud import get_user_by_id, update_user_profile
from app.schemas.user_schema import UserResponse, UserUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

@router.put("/profile/{user_id}", response_model=UserResponse)
def update_profile(user_id: str, user_update: UserUpdate, db: Database = Depends(get_db)):
    """Update user profile information"""
    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user
    updated_user = update_user_profile(db, user_id, user_update.model_dump(exclude_unset=True))
    
    if not updated_user:
        raise HTTPException(status_code=400, detail="Failed to update profile")
        
    return updated_user

from app.schemas.user_schema import ChangePasswordRequest
from app.crud.user_crud import change_password

@router.post("/profile/{user_id}/password")
def change_user_password(user_id: str, password_data: ChangePasswordRequest, db: Database = Depends(get_db)):
    """Change user password"""
    # Verify user exists
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    success = change_password(db, user_id, password_data.current_password, password_data.new_password)
    
    if not success:
        raise HTTPException(status_code=400, detail="Invalid current password")
        
    return {"message": "Password changed successfully"}
@router.get("/community/members")
def get_community_members(db: Database = Depends(get_db)):
    """Fetch all users to display in the community member list"""
    try:
        users_cursor = db.users.find({}, {
            "user_id": 1,
            "first_name": 1,
            "last_name": 1,
            "role": 1,
            "last_seen": 1
        })
        users = list(users_cursor)
        
        # Format for response
        results = []
        for user in users:
            try:
                # Ensure user_id exists
                uid = user.get("user_id")
                if not uid:
                    continue
                    
                results.append({
                    "user_id": uid,
                    "name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Anonymous",
                    "role": user.get("role", "user"),
                    "last_seen": user.get("last_seen").isoformat() + "Z" if user.get("last_seen") and hasattr(user.get("last_seen"), 'isoformat') else None
                })
            except Exception as e:
                logger.error(f"Error formatting user in community list: {e}")
                continue
        
        logger.info(f"Community members list fetched: {len(results)} users")
        return results
    except Exception as e:
        logger.error(f"Error fetching community members: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
