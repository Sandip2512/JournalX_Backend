from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: str
    username: str
    email: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_profit: float
    total_profit: float
    total_loss: float
    avg_profit_per_trade: float
    best_trade: float
    worst_trade: float
    profit_factor: float
    created_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UserRankingResponse(BaseModel):
    user_rank: LeaderboardEntry
    total_users: int
    percentile: float
    
    class Config:
        from_attributes = True
