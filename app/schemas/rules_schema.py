from pydantic import BaseModel, Field
from typing import Optional, List

class TradingRulesBase(BaseModel):
    max_risk_per_trade: float = Field(..., description="Max risk per trade (%)")
    max_daily_loss: float = Field(..., description="Max daily loss (%)")
    max_trades_per_day: int = Field(..., description="Max trades allowed per day")
    max_losing_trades: int = Field(..., description="Max losing trades allowed per day")
    risk_reward: str = Field(..., description="Target Risk:Reward ratio (e.g., '1:2')")
    sessions: List[str] = Field(default_factory=list, description="Preferred trading sessions")
    pairs: List[str] = Field(default_factory=list, description="Favorite pairs to trade")

class TradingRulesCreate(TradingRulesBase):
    pass

class TradingRulesUpdate(BaseModel):
    max_risk_per_trade: Optional[float] = None
    max_daily_loss: Optional[float] = None
    max_trades_per_day: Optional[int] = None
    max_losing_trades: Optional[int] = None
    risk_reward: Optional[str] = None
    sessions: Optional[List[str]] = None
    pairs: Optional[List[str]] = None

class TradingRulesResponse(TradingRulesBase):
    id: str
    user_id: str
    month: str = Field(..., description="Month in YYYY-MM format")
    version: int
    created_at: str

    class Config:
        from_attributes = True
