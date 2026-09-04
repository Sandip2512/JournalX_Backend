from fastapi import APIRouter, Depends, HTTPException, Body
from pymongo.database import Database
from typing import Dict, Any

from app.mongo_database import get_db
from app.routes.auth import get_current_user
from app.crud.rules_crud import create_or_update_rules, get_rules_for_month, copy_last_month_rules
from app.crud.preferences_crud import create_or_update_preferences, get_preferences
from app.schemas.rules_schema import TradingRulesCreate, TradingRulesResponse
from app.schemas.preferences_schema import PreferencesCreate, PreferencesResponse

router = APIRouter()

@router.post("/setup")
def complete_onboarding_setup(
    setup_data: Dict[str, Any] = Body(...),
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Submits all onboarding data at once and marks onboarding as completed.
    Expects:
    {
      "rules": TradingRulesCreate,
      "preferences": PreferencesCreate
    }
    """
    try:
        if "rules" in setup_data:
            rules_create = TradingRulesCreate(**setup_data["rules"])
            create_or_update_rules(db, current_user["user_id"], rules_create)
            
        if "preferences" in setup_data:
            prefs_create = PreferencesCreate(**setup_data["preferences"])
            create_or_update_preferences(db, current_user["user_id"], prefs_create)
            
        # Update user profile
        db.users.update_one(
            {"user_id": current_user["user_id"]},
            {"$set": {"is_onboarding_completed": True}}
        )
        
        return {"status": "success", "message": "Onboarding completed successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/status")
def get_onboarding_status(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Returns user onboarding status and flags.
    """
    user = db.users.find_one({"user_id": current_user["user_id"]})
    return {
        "is_onboarding_completed": user.get("is_onboarding_completed", False)
    }

@router.get("/rules/current")
def get_current_rules(
    month: str = None,
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """Get rules for the current month or specified month"""
    rules = get_rules_for_month(db, current_user["user_id"], month)
    if not rules:
        raise HTTPException(status_code=404, detail="No rules found for this month")
    return rules

@router.post("/rules/copy-last-month")
def copy_previous_month_rules(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    rules = copy_last_month_rules(db, current_user["user_id"])
    if not rules:
        raise HTTPException(status_code=404, detail="No previous rules to copy")
    return rules

@router.get("/preferences")
def get_user_preferences(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    prefs = get_preferences(db, current_user["user_id"])
    if not prefs:
        return {"currency": "USD", "timezone": "UTC"}
    return prefs
