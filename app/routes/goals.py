from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.mongo_database import get_db
from app.schemas.goal_schema import GoalCreate, GoalUpdate, GoalResponse
from typing import Optional
from datetime import datetime

router = APIRouter(
    tags=["Goals"],
    responses={404: {"description": "Not found"}},
)

@router.get("/user/{user_id}", response_model=GoalResponse)
def get_user_goal(user_id: str, db: Database = Depends(get_db)):
    """Get goals for a specific user"""
    goal = db.goals.find_one({"user_id": user_id})
    if not goal:
        raise HTTPException(status_code=404, detail="No goals found for this user")
    return goal

@router.post("/", response_model=GoalResponse)
def create_or_update_goal(goal_data: GoalCreate, user_id: str, db: Database = Depends(get_db)):
    """Create or update user goals"""
    existing = db.goals.find_one({"user_id": user_id})
    
    new_data = goal_data.model_dump()
    new_data["user_id"] = user_id
    new_data["updated_at"] = datetime.now()
    
    if not existing:
        new_data["created_at"] = datetime.now()
        # MongoDB _id will be used as internal id, but we can set an 'id' field for consistency if we want
        # but the schema expects GoalResponse which has 'id'. 
        # Let's map _id to id in the response or use a UUID.
        import uuid
        new_data["id"] = str(uuid.uuid4())
        db.goals.insert_one(new_data)
    else:
        db.goals.update_one(
            {"user_id": user_id},
            {"$set": new_data}
        )
    
    return db.goals.find_one({"user_id": user_id})

@router.put("/user/{user_id}", response_model=GoalResponse)
def update_goal(user_id: str, goal_update: GoalUpdate, db: Database = Depends(get_db)):
    """Update specific fields of a user's goal"""
    update_data = goal_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    
    existing = db.goals.find_one({"user_id": user_id})
    
    if not existing:
        import uuid
        update_data["user_id"] = user_id
        update_data["created_at"] = datetime.now()
        update_data["id"] = str(uuid.uuid4())
        db.goals.insert_one(update_data)
    else:
        db.goals.update_one(
            {"user_id": user_id},
            {"$set": update_data}
        )
    
    return db.goals.find_one({"user_id": user_id})

