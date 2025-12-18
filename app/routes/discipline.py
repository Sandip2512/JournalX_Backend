from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.mongo_database import get_db
from app.schemas.discipline_schema import DisciplineDayResponse, DisciplineStatsResponse
from typing import List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter(
    tags=["Discipline"],
    responses={404: {"description": "Not found"}},
)

def calculate_daily_discipline(db: Database, user_id: str, target_date: datetime, saved_goals: dict):
    """Calculate discipline compliance for a specific day"""
    # Get trades for the day
    start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = target_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    trades = list(db.trades.find({
        "user_id": user_id,
        "close_time": {"$gte": start_of_day, "$lte": end_of_day}
    }))
    
    total_trades = len(trades)
    daily_pnl = sum(t.get("net_profit", 0) for t in trades)
    
    # Check rules
    followed_loss_limit = True
    followed_trade_limit = True
    on_track_profit = True
    
    # Rule 1: Daily Loss Limit
    if saved_goals.get("max_daily_loss", 0) > 0:
        if daily_pnl < 0 and abs(daily_pnl) >= saved_goals["max_daily_loss"]:
            followed_loss_limit = False
    
    # Rule 2: Max Trades Per Day
    if saved_goals.get("max_trades_per_day", 0) > 0:
        if total_trades > saved_goals["max_trades_per_day"]:
            followed_trade_limit = False
    
    # Rule 3: Monthly Progress (simplified - just check if profitable)
    if saved_goals.get("monthly_profit_target", 0) > 0:
        # For now, just check if the day was profitable
        on_track_profit = daily_pnl >= 0
    
    all_rules_followed = followed_loss_limit and followed_trade_limit and on_track_profit
    
    return {
        "date": target_date.date(),
        "user_id": user_id,
        "followed_loss_limit": followed_loss_limit,
        "followed_trade_limit": followed_trade_limit,
        "on_track_profit": on_track_profit,
        "total_trades": total_trades,
        "daily_pnl": daily_pnl,
        "all_rules_followed": all_rules_followed
    }

@router.get("/history/{user_id}", response_model=List[DisciplineDayResponse])
def get_discipline_history(user_id: str, days: int = 30, db: Database = Depends(get_db)):
    """Get discipline diary for last N days"""
    try:
        # Get user's saved goals
        goals = db.goals.find_one({"user_id": user_id})
        if not goals:
            goals = {"max_daily_loss": 0, "max_trades_per_day": 0, "monthly_profit_target": 0}
        
        # Calculate discipline for each day
        today = datetime.now()
        history = []
        
        for i in range(days):
            target_date = today - timedelta(days=i)
            day_discipline = calculate_daily_discipline(db, user_id, target_date, goals)
            history.append(day_discipline)
        
        return history
    except Exception as e:
        logger.error(f"Error getting discipline history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stats/{user_id}", response_model=DisciplineStatsResponse)
def get_discipline_stats(user_id: str, days: int = 30, db: Database = Depends(get_db)):
    """Get discipline statistics and streaks"""
    try:
        # Get history
        history = get_discipline_history(user_id, days, db)
        
        total_days = len(history)
        compliant_days = sum(1 for d in history if d["all_rules_followed"])
        violation_days = total_days - compliant_days
        compliance_rate = (compliant_days / total_days * 100) if total_days > 0 else 0
        
        # Calculate streaks
        current_streak = 0
        best_streak = 0
        worst_streak = 0
        temp_streak = 0
        temp_violation_streak = 0
        
        for day in reversed(history):  # Start from oldest
            if day["all_rules_followed"]:
                temp_streak += 1
                temp_violation_streak = 0
                best_streak = max(best_streak, temp_streak)
            else:
                temp_violation_streak += 1
                temp_streak = 0
                worst_streak = max(worst_streak, temp_violation_streak)
        
        # Current streak is the most recent
        for day in history:  # Start from most recent
            if day["all_rules_followed"]:
                current_streak += 1
            else:
                break
        
        return {
            "total_days": total_days,
            "compliant_days": compliant_days,
            "violation_days": violation_days,
            "compliance_rate": round(compliance_rate, 1),
            "current_streak": current_streak,
            "best_streak": best_streak,
            "worst_streak": worst_streak
        }
    except Exception as e:
        logger.error(f"Error getting discipline stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
