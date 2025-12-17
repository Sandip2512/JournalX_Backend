from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.mongo_database import get_db
from app.crud.user_crud import get_user_by_id, update_user_profile
from app.schemas.user_schema import UserResponse, UserUpdate

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
