from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.mongo_database import get_db
from app.schemas.goal_schema import GoalCreate, GoalUpdate, GoalResponse
from typing import Optional

router = APIRouter(
    prefix="/goals",
    tags=["Goals"],
    responses={404: {"description": "Not found"}},
)

@router.get("/user/{user_id}", response_model=GoalResponse)
def get_user_goal(user_id: str, db: Database = Depends(get_db)):
    """Get goals for a specific user"""
    goal = db.goals.find_one({"user_id": user_id})
    if not goal:
        # Return default empty goal instead of 404 to simplify frontend
        return {
            "user_id": user_id, 
            "monthly_profit_target": 0, 
            "max_daily_loss": 0, 
            "max_trades_per_day": 0
        }
    return goal

@router.post("/", response_model=GoalResponse)
def create_or_update_goal(goal_data: GoalCreate, user_id: str, db: Database = Depends(get_db)):
    """Create or update user goals"""
    # Use update_one with upsert=True
    new_data = goal_data.dict()
    new_data["user_id"] = user_id
    
    db.goals.update_one(
        {"user_id": user_id},
        {"$set": new_data},
        upsert=True
    )
    
    # Fetch and return
    return db.goals.find_one({"user_id": user_id})

@router.put("/user/{user_id}", response_model=GoalResponse)
def update_goal(user_id: str, goal_update: GoalUpdate, db: Database = Depends(get_db)):
    """Update specific fields of a user's goal"""
    update_data = goal_update.dict(exclude_unset=True)
    
    if not update_data:
        # Nothing to update, return existing or default
        goal = db.goals.find_one({"user_id": user_id})
        if not goal:
            # Create default if missing
             db.goals.insert_one({
                "user_id": user_id, 
                "monthly_profit_target": 0, 
                "max_daily_loss": 0, 
                "max_trades_per_day": 0
            })
             return db.goals.find_one({"user_id": user_id})
        return goal

    result = db.goals.update_one(
        {"user_id": user_id},
        {"$set": update_data},
        upsert=True  # Create if doesn't exist
    )
    
    # If we upserted but didn't have all fields, we might have partial doc. 
    # But schema validation handles response.
    # Ideally should ensure user_id is set if it was an insert.
    if result.upserted_id:
        # Ensure user_id is in the set if it's a fresh doc, though $set won't set it if it's not in update_data
        # Wait, if update_data doesn't have user_id and we upsert based on query {"user_id": user_id}, 
        # MongoDB < 2.6 didn't insert query fields. Newer ones do. 
        # To be safe, include user_id in $set or $setOnInsert if we cared.
        # But here valid goal_update doesn't have user_id usually.
        # Let's explicitly ensure user_id is set.
        db.goals.update_one({"_id": result.upserted_id}, {"$set": {"user_id": user_id}})

    return db.goals.find_one({"user_id": user_id})

