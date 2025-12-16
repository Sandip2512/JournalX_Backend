from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class TradeBase(BaseModel):
    user_id: str
    trade_no: Optional[int] = None  # Auto-generated, optional for creation
    symbol: str
    volume: float
    price_open: float
    price_close: float
    type: str
    take_profit: Optional[float] = 0.0
    stop_loss: Optional[float] = 0.0
    profit_amount: float
    loss_amount: float
    net_profit: Optional[float] = None
    reason: Optional[str] = None
    mistake: Optional[str] = None
    
    # Advanced Analytics
    r_multiple: Optional[float] = None
    risk_percentage: Optional[float] = None
    mae: Optional[float] = None
    mfe: Optional[float] = None
    strategy: Optional[str] = None
    session: Optional[str] = None
    emotion: Optional[str] = None
    open_time: datetime
    close_time: datetime

class TradeCreate(TradeBase):
    pass

class Trade(TradeBase):
    id: int

    class Config:
        from_attributes = True   # ✅ fixed for Pydantic v2
