from fastapi import APIRouter, Depends, HTTPException
from pymongo.database import Database
from app.mongo_database import get_db
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/stats/user/{user_id}")
def get_user_trade_stats(user_id: str, db: Database = Depends(get_db)):
    """
    Get aggregated trade statistics for a user.
    Returns: total_trades, net_profit, win_rate, avg_win, avg_loss, max_win, max_loss, closed_trades, profit_factor
    """
    try:
        # Get user for subscription info
        user = db.users.find_one({"user_id": user_id})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        sub_tier = user.get("subscription_tier", "free")
        is_free_tier = sub_tier == "free"
        
        # Build query
        query = {"user_id": user_id}
        
        # Free tier restriction: Last 30 days only
        if is_free_tier:
            limit_date = datetime.now() - timedelta(days=30)
            query["$or"] = [
                {"close_time": {"$gte": limit_date}},
                {"close_time": None, "open_time": {"$gte": limit_date}}
            ]
        
        # Fetch all trades
        trades = list(db.trades.find(query))
        
        if not trades:
            return {
                "total_trades": 0,
                "net_profit": 0.0,
                "win_rate": 0.0,
                "avg_win": 0.0,
                "avg_loss": 0.0,
                "max_win": 0.0,
                "max_loss": 0.0,
                "closed_trades": 0,
                "profit_factor": 0.0,
                "total_profit": 0.0,
                "total_loss": 0.0,
                "winning_trades": 0,
                "losing_trades": 0,
                "is_free_tier": is_free_tier
            }
        
        # Calculate statistics
        total_trades = len(trades)
        closed_trades = len([t for t in trades if t.get("close_time")])
        
        # Calculate net profit
        net_profits = []
        for t in trades:
            net = t.get("net_profit")
            if net is None:
                net = t.get("profit_amount", 0.0) - t.get("loss_amount", 0.0)
            net_profits.append(net)
        
        total_net_profit = sum(net_profits)
        
        # Wins and losses
        wins = [p for p in net_profits if p > 0]
        losses = [p for p in net_profits if p <= 0]
        
        win_count = len(wins)
        win_rate = (win_count / total_trades * 100) if total_trades > 0 else 0.0
        
        avg_win = sum(wins) / len(wins) if wins else 0.0
        avg_loss = sum(losses) / len(losses) if losses else 0.0
        
        max_win = max(net_profits) if net_profits else 0.0
        max_loss = min(net_profits) if net_profits else 0.0
        
        # Profit factor
        total_wins = sum(wins) if wins else 0.0
        total_losses = abs(sum(losses)) if losses else 0.0
        profit_factor = total_wins / total_losses if total_losses > 0 else 0.0
        
        return {
            "total_trades": total_trades,
            "net_profit": round(total_net_profit, 2),
            "win_rate": round(win_rate, 2),
            "avg_win": round(avg_win, 2),
            "avg_loss": round(avg_loss, 2),
            "max_win": round(max_win, 2),
            "max_loss": round(max_loss, 2),
            "closed_trades": closed_trades,
            "profit_factor": round(profit_factor, 2),
            "total_profit": round(total_wins, 2),
            "total_loss": round(total_losses, 2),
            "winning_trades": win_count,
            "losing_trades": len(losses),
            "is_free_tier": is_free_tier
        }
        
    except Exception as e:
        logger.error(f"Error calculating trade stats for user {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")
