from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo.database import Database
from typing import List, Optional
from app.mongo_database import get_db
# from app.models.user import User
from app.routes.admin import get_current_user_role
from app.crud.user_crud import get_user_by_id, get_password_hash
from pydantic import BaseModel, EmailStr
from datetime import datetime

router = APIRouter()

# --- Schemas ---
class UserEditRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    mobile_number: Optional[str] = None
    role: Optional[str] = None

class UserStatusRequest(BaseModel):
    is_active: bool

class PasswordResetRequest(BaseModel):
    password: str

# --- Endpoints ---

@router.get("/{user_id}/history")
def get_user_login_history(
    user_id: str,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    logs = list(db.login_history.find({"user_id": user_id}).sort("timestamp", -1).limit(50))
    # Convert _id to string
    for log in logs:
        log["id"] = str(log.pop("_id"))
    return logs

@router.put("/{user_id}")
def update_user_details(
    user_id: str,
    user_update: UserEditRequest,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    update_data = {}
    if user_update.first_name: update_data["first_name"] = user_update.first_name
    if user_update.last_name: update_data["last_name"] = user_update.last_name
    if user_update.email: update_data["email"] = user_update.email
    if user_update.mobile_number: update_data["mobile_number"] = user_update.mobile_number
    if user_update.role: update_data["role"] = user_update.role
    
    if update_data:
        db.users.update_one({"user_id": user_id}, {"$set": update_data})
        user.update(update_data)
        
    user.pop("_id", None)
    return {"message": "User updated successfully", "user": user}

@router.patch("/{user_id}/status")
def update_user_status(
    user_id: str,
    status: UserStatusRequest,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    result = db.users.update_one({"user_id": user_id}, {"$set": {"is_active": status.is_active}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": f"User {'activated' if status.is_active else 'deactivated'} successfully"}

@router.post("/{user_id}/reset-password")
def admin_reset_password(
    user_id: str,
    reset: PasswordResetRequest,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    hashed_pw = get_password_hash(reset.password)
    result = db.users.update_one({"user_id": user_id}, {"$set": {"password": hashed_pw}})
    
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
        
    return {"message": "Password reset successfully"}
