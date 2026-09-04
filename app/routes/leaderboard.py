from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.mongo_database import get_db
# from app.models.user import User  <-- Removing models
# from app.models.trade import Trade
from app.schemas.leaderboard_schema import LeaderboardEntry, UserRankingResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def calculate_leaderboard_stats(db: Database, time_period: Optional[str] = "all_time"):
    """
    Calculate leaderboard statistics for all users
    """
    # Determine time filter
    time_filter = {}
    if time_period == "weekly":
        start_date = datetime.now() - timedelta(days=7)
        time_filter = {"close_time": {"$gte": start_date}}
    elif time_period == "monthly":
        start_date = datetime.now() - timedelta(days=30)
        time_filter = {"close_time": {"$gte": start_date}}
    elif time_period == "daily":
        start_date = datetime.now() - timedelta(days=1)
        time_filter = {"close_time": {"$gte": start_date}}
    
    # Get all users (role="user")
    users = list(db.users.find({"role": "user"}))
    
    leaderboard_data = []
    
    for user in users:
        # Query trades for this user with time filter
        query = {"user_id": user["user_id"]}
        if time_filter:
            query.update(time_filter)
            
        trades = list(db.trades.find(query))
        
        # Skip users with no trades (if that's the desired behavior per original code)
        if not trades:
            continue
        
        # Calculate statistics
        # Note: In production with many users, this should be an aggregation pipeline.
        # But for migration correctness first, Python iteration is safer to replicate exact logic.
        
        total_trades = len(trades)
        winning_trades = sum(1 for t in trades if (t.get("net_profit") or 0) > 0)
        losing_trades = sum(1 for t in trades if (t.get("net_profit") or 0) <= 0)
        win_rate = (winning_trades / total_trades * 100) if total_trades > 0 else 0
        
        total_profit = sum((t.get("profit_amount") or 0) for t in trades)
        total_loss = sum((t.get("loss_amount") or 0) for t in trades)
        
        # Calculate net_profit with fallback
        net_profit = sum(
            (t.get("net_profit") if t.get("net_profit") is not None else (t.get("profit_amount", 0.0) - t.get("loss_amount", 0.0)))
            for t in trades
        )
        
        avg_profit_per_trade = net_profit / total_trades if total_trades > 0 else 0
        
        # Best/Worst
        profits = [(t.get("net_profit") or 0) for t in trades]
        best_trade = max(profits, default=0)
        worst_trade = min(profits, default=0)
        
        # Calculate profit factor (total profit / total loss)
        profit_factor = (total_profit / total_loss) if total_loss > 0 else (total_profit if total_profit > 0 else 0)
        
        # Create username
        first_name = user.get("first_name", "")
        last_name = user.get("last_name", "")
        username = f"{first_name} {last_name}".strip()
        if not username:
            username = user.get("email", "").split('@')[0]
        
        leaderboard_data.append({
            'user_id': user["user_id"],
            'username': username,
            'email': user["email"],
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': round(win_rate, 2),
            'net_profit': round(net_profit, 2),
            'total_profit': round(total_profit, 2),
            'total_loss': round(total_loss, 2),
            'avg_profit_per_trade': round(avg_profit_per_trade, 2),
            'best_trade': round(best_trade, 2),
            'worst_trade': round(worst_trade, 2),
            'profit_factor': round(profit_factor, 2),
            'created_at': user.get("created_at")
        })
    
    return leaderboard_data


@router.get("/", response_model=List[LeaderboardEntry])
def get_leaderboard(
    sort_by: str = Query("net_profit", pattern="^(net_profit|win_rate|total_trades|profit_factor)$"),
    limit: int = Query(100, ge=1, le=500),
    time_period: str = Query("all_time", pattern="^(all_time|monthly|weekly|daily)$"),
    db: Database = Depends(get_db)
):
    """
    Get leaderboard with all users ranked by specified metric
    """
    try:
        # Calculate statistics
        leaderboard_data = calculate_leaderboard_stats(db, time_period)
        
        # Sort by specified metric (descending)
        leaderboard_data.sort(key=lambda x: x[sort_by], reverse=True)
        
        # Limit results
        leaderboard_data = leaderboard_data[:limit]
        
        # Add rank
        for idx, entry in enumerate(leaderboard_data, start=1):
            entry['rank'] = idx
        
        return leaderboard_data
    
    except Exception as e:
        logger.error(f"Error fetching leaderboard: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching leaderboard: {str(e)}")


@router.get("/user/{user_id}", response_model=UserRankingResponse)
def get_user_ranking(
    user_id: str,
    sort_by: str = Query("net_profit", pattern="^(net_profit|win_rate|total_trades|profit_factor)$"),
    time_period: str = Query("all_time", pattern="^(all_time|monthly|weekly|daily)$"),
    db: Database = Depends(get_db)
):
    """
    Get specific user's ranking and statistics
    """
    try:
        # Verify user exists
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Calculate full leaderboard
        leaderboard_data = calculate_leaderboard_stats(db, time_period)
        
        # Sort by specified metric
        leaderboard_data.sort(key=lambda x: x[sort_by], reverse=True)
        
        # Find user's position
        user_rank_data = None
        total_users = len(leaderboard_data)
        
        for idx, entry in enumerate(leaderboard_data, start=1):
            entry['rank'] = idx
            if entry['user_id'] == user_id:
                user_rank_data = entry
        
        if not user_rank_data:
            # Maybe user has no trades and was skipped in calculate_leaderboard_stats
            # We can construct a zero-entry if we want, or match original behavior (404/error)
            # Original code said "User has no trades yet" (implied by calculate loop skipping empty trades users)
            # Wait, original loop: "if not trades: continue". So if user has no trades, they are not in leaderboard_data.
            raise HTTPException(status_code=404, detail="User has no trades yet")
        
        # Calculate percentile
        percentile = ((total_users - user_rank_data['rank']) / total_users * 100) if total_users > 0 else 0
        
        return {
            'user_rank': user_rank_data,
            'total_users': total_users,
            'percentile': round(percentile, 2)
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching user ranking: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching user ranking: {str(e)}")

