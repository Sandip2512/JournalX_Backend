from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class GoalBase(BaseModel):
    monthly_profit_target: Optional[float] = 0.0
    max_daily_loss: Optional[float] = 0.0
    max_trades_per_day: Optional[int] = 0
    is_active: Optional[bool] = True

class GoalCreate(GoalBase):
    pass

class GoalUpdate(GoalBase):
    pass

class GoalResponse(GoalBase):
    id: int
    user_id: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
