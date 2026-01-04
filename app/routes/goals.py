from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from app.mongo_database import get_db
from app.schemas.goal_schema import GoalCreate, GoalUpdate, GoalResponse
from typing import Optional, List
from datetime import datetime

router = APIRouter(
    tags=["Goals"],
    responses={404: {"description": "Not found"}},
)

@router.get("/user/{user_id}", response_model=List[GoalResponse])
def get_user_goals(user_id: str, db: Database = Depends(get_db)):
    """Get all active goals with automatic production data repair"""
    # --- AUTO-REPAIR SECTION ---
    # Fix 1: Reactivate goals that were accidentally hidden by the achievement bug
    db.goals.update_many(
        {"user_id": user_id, "is_active": False, "target_amount": {"$gt": 0}},
        {"$set": {"is_active": True}}
    )

    # Fix 2: Migrate legacy field names (weekly_profit_target -> target_amount)
    legacy = list(db.goals.find({
        "user_id": user_id,
        "target_amount": {"$exists": False},
        "$or": [{"weekly_profit_target": {"$exists": True}}, {"monthly_profit_target": {"$exists": True}}]
    }))
    for lg in legacy:
        target = lg.get("weekly_profit_target") or lg.get("monthly_profit_target") or 0
        g_type = "weekly" if lg.get("weekly_profit_target") else "monthly"
        db.goals.update_one(
            {"_id": lg["_id"]},
            {"$set": {"target_amount": float(target), "goal_type": g_type, "is_active": True}}
        )

    # --- FINAL FETCH ---
    goals = list(db.goals.find({"user_id": user_id, "is_active": True}))
    return goals

@router.get("/user/{user_id}/achieved", response_model=List[GoalResponse])
def get_achieved_goals(user_id: str, db: Database = Depends(get_db)):
    """Get all achieved goals for a user"""
    achieved_goals = list(db.goals.find({"user_id": user_id, "achieved": True}).sort("achieved_date", -1))
    return achieved_goals

@router.post("/", response_model=GoalResponse)
def create_or_update_goal(goal_data: GoalCreate, user_id: str, db: Database = Depends(get_db)):
    """Create or update user goals"""
    # Check for existing active goal of THIS TYPE
    existing = db.goals.find_one({
        "user_id": user_id, 
        "is_active": True, 
        "goal_type": goal_data.goal_type
    })
    
    new_data = goal_data.model_dump()
    new_data["user_id"] = user_id
    new_data["updated_at"] = datetime.now()
    
    # Auto-set month/year/week based on goal_type
    now = datetime.now()
    if new_data.get("goal_type") == "weekly":
        new_data["week"] = now.isocalendar()[1]  # ISO week number
        new_data["year"] = now.year
        new_data["month"] = None
    elif new_data.get("goal_type") == "monthly":
        new_data["month"] = now.month
        new_data["year"] = now.year
        new_data["week"] = None
    elif new_data.get("goal_type") == "yearly":
        new_data["year"] = now.year
        new_data["month"] = None
        new_data["week"] = None
    
    if not existing:
        new_data["created_at"] = datetime.now()
        import uuid
        new_data["id"] = str(uuid.uuid4())
        db.goals.insert_one(new_data)
        return db.goals.find_one({"id": new_data["id"]})
    else:
        db.goals.update_one(
            {"_id": existing["_id"]}, # Safer to update by _id
            {"$set": new_data}
        )
        return db.goals.find_one({"_id": existing["_id"]})

@router.put("/user/{user_id}", response_model=GoalResponse)
def update_goal(user_id: str, goal_update: GoalUpdate, db: Database = Depends(get_db)):
    """Update specific fields of a user's goal"""
    update_data = goal_update.model_dump(exclude_unset=True)
    update_data["updated_at"] = datetime.now()
    
    existing = db.goals.find_one({"user_id": user_id, "is_active": True})
    
    if not existing:
        import uuid
        update_data["user_id"] = user_id
        update_data["created_at"] = datetime.now()
        update_data["id"] = str(uuid.uuid4())
        
        # Auto-set month/year/week
        now = datetime.now()
        if update_data.get("goal_type") == "weekly":
            update_data["week"] = now.isocalendar()[1]
            update_data["year"] = now.year
            update_data["month"] = None
        elif update_data.get("goal_type") == "monthly":
            update_data["month"] = now.month
            update_data["year"] = now.year
            update_data["week"] = None
        elif update_data.get("goal_type") == "yearly":
            update_data["year"] = now.year
            update_data["month"] = None
            update_data["week"] = None
            
        db.goals.insert_one(update_data)
    else:
        db.goals.update_one(
            {"user_id": user_id, "is_active": True},
            {"$set": update_data}
        )
    
    return db.goals.find_one({"user_id": user_id, "is_active": True})

@router.post("/user/{user_id}/mark-achieved")
def mark_goal_achieved(user_id: str, goal_id: str, db: Database = Depends(get_db)):
    """Mark a goal as achieved"""
    result = db.goals.update_one(
        {"user_id": user_id, "id": goal_id},
        {"$set": {"achieved": True, "achieved_date": datetime.now(), "is_active": False}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Goal not found")
    
    return {"message": "Goal marked as achieved"}

@router.delete("/user/{user_id}")
def delete_active_goal(user_id: str, goal_type: Optional[str] = None, db: Database = Depends(get_db)):
    """Delete active goal(s) for a user. Optional: specify goal_type to delete only one."""
    query = {"user_id": user_id, "is_active": True}
    if goal_type:
        query["goal_type"] = goal_type.lower()
        
    result = db.goals.delete_many(query)
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="No active goal found to delete")
    
    return {"message": "Goal(s) deleted successfully", "deleted_count": result.deleted_count}
