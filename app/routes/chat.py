from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from app.mongo_database import get_db
from app.crud.user_crud import get_user_by_email
from app.routes.auth import get_current_user
from pymongo.database import Database
from app.services.ai_service import ai_service

from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
import os
from typing import Optional
from app.routes.auth import SECRET_KEY, ALGORITHM

router = APIRouter()

class ChatRequest(BaseModel):
    message: str

class ChatResponse(BaseModel):
    response: str

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

async def get_current_user_optional(token: Optional[str] = Depends(oauth2_scheme), db: Database = Depends(get_db)) -> Optional[dict]:
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            return None
        # Quick lookup, don't raise error if not found to allow guest degradation
        user = db.users.find_one({"email": email})
        return user
    except JWTError:
        return None

@router.post("/message", response_model=ChatResponse)
async def chat_message(
    request: ChatRequest,
    current_user: Optional[dict] = Depends(get_current_user_optional),
    db: Database = Depends(get_db)
):
    """
    Send a message to the AI and get a response.
    Supports both authenticated users and guests.
    """
    if not request.message:
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    
    user_id = current_user.get("user_id") if current_user else None
    
    # Pass user_id (or None) and db to get_response
    response_text = await ai_service.get_response(request.message, user_id, db)
    return ChatResponse(response=response_text)
