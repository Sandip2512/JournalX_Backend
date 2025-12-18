from pydantic import BaseModel
from typing import Optional
from datetime import date

class DisciplineDayBase(BaseModel):
    date: date
    followed_loss_limit: bool = True
    followed_trade_limit: bool = True
    on_track_profit: bool = True
    
class DisciplineDayResponse(DisciplineDayBase):
    user_id: str
    total_trades: int = 0
    daily_pnl: float = 0.0
    all_rules_followed: bool = True
    
    class Config:
        from_attributes = True

class DisciplineStatsResponse(BaseModel):
    total_days: int
    compliant_days: int
    violation_days: int
    compliance_rate: float
    current_streak: int
    best_streak: int
    worst_streak: int
