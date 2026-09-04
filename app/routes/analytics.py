from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from app.mongo_database import get_db
from app.services.analytics_service import calculate_analytics, get_calendar_stats, get_weekly_review_stats, generate_insights, get_diary_stats
from typing import Dict, Any, List, Optional
from datetime import datetime

router = APIRouter()

@router.get("/user/{user_id}")
async def get_user_analytics(user_id: str, db: Database = Depends(get_db)):
    """
    Get progressive analytics for a specific user.
    """
    try:
        analytics = calculate_analytics(db, user_id)
        return analytics
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error calculating analytics: {str(e)}")

@router.get("/calendar", response_model=List[Dict])
def get_calendar(user_id: str, month: int, year: int, db: Database = Depends(get_db)):
    """Get daily P&L for calendar view"""
    return get_calendar_stats(db, user_id, month, year)

@router.get("/weekly-review", response_model=Dict)
def get_weekly_review(
    user_id: str, 
    start_date: Optional[str] = None, 
    end_date: Optional[str] = None, 
    db: Database = Depends(get_db)
):
    """
    Get stats for review.
    Dates should be in ISO format (YYYY-MM-DD).
    If not provided, defaults to last 7 days.
    """
    start = None
    end = None
    
    try:
        if start_date:
            start = datetime.fromisoformat(start_date)
            # Ensure it starts at beginning of day if just date provided
            if len(start_date) == 10:
                 start = start.replace(hour=0, minute=0, second=0)
                 
        if end_date:
            end = datetime.fromisoformat(end_date)
             # Ensure it includes the whole day if just date provided
            if len(end_date) == 10:
                 end = end.replace(hour=23, minute=59, second=59)
                 
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")

    return get_weekly_review_stats(db, user_id, start, end)

@router.get("/insights", response_model=List[Dict])
def get_insights(user_id: str, db: Database = Depends(get_db)):
    """Get smart insights"""
    return generate_insights(db, user_id)

@router.get("/diary", response_model=Dict)
def get_diary(
    user_id: str, 
    start_date: str, 
    end_date: str, 
    db: Database = Depends(get_db)
):
    """
    Get Trader's Diary stats.
    Dates are required in ISO format (YYYY-MM-DD).
    """
    try:
        start = datetime.fromisoformat(start_date)
        if len(start_date) == 10:
             start = start.replace(hour=0, minute=0, second=0)
             
        end = datetime.fromisoformat(end_date)
        if len(end_date) == 10:
             end = end.replace(hour=23, minute=59, second=59)
                 
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Use ISO format (YYYY-MM-DD)")

    return get_diary_stats(db, user_id, start, end)
