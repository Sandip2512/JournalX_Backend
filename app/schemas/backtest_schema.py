from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class BacktestSessionBase(BaseModel):
    strategy_name: str
    pairs: List[str]
    timeframe: str
    start_date: datetime
    end_date: datetime
    starting_balance: float
    mode: str = "backtest" # "backtest", "live", or "tv_sync"
    tv_email: Optional[str] = None

class BacktestSessionCreate(BacktestSessionBase):
    pass

class BacktestSession(BacktestSessionBase):
    id: str = Field(alias="_id")
    user_id: str
    created_at: datetime
    status: str = "active" # "active", "completed", "paused"

    class Config:
        populate_by_name = True
        from_attributes = True

class BacktestTradeBase(BaseModel):
    pair: str
    entry_time: datetime
    exit_time: Optional[datetime] = None
    entry_price: float
    exit_price: Optional[float] = None
    lot_size: float
    trade_type: str # "buy" or "sell"
    tp_price: Optional[float] = None
    sl_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    tags: Optional[List[str]] = []
    status: str = "open" # "open", "closed"

class BacktestTradeCreate(BacktestTradeBase):
    session_id: str

class BacktestTrade(BacktestTradeBase):
    id: str = Field(alias="_id")
    session_id: str
    user_id: str
    profit_loss: float = 0.0

    class Config:
        populate_by_name = True
        from_attributes = True

class BacktestStats(BaseModel):
    session_id: str
    total_trades: int = 0
    win_rate: float = 0.0
    net_pnl: float = 0.0
    max_drawdown: float = 0.0
    avg_rr: float = 0.0
    equity_curve: List[dict] = [] # List of {timestamp, equity}
