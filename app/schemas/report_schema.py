from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any

class PerformanceReportBase(BaseModel):
    report_type: str  # 'weekly', 'monthly', 'yearly'
    start_date: datetime
    end_date: datetime
    filename: str
    status: str = "completed"  # 'pending', 'completed', 'failed'

class PerformanceReportCreate(PerformanceReportBase):
    user_id: str

class PerformanceReportResponse(PerformanceReportBase):
    id: str
    user_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ReportInsights(BaseModel):
    summary: str
    strengths: List[str]
    weaknesses: List[str]
    patterns: List[str]
    mistakes: List[str]
    suggestions: List[str]

class ReportStats(BaseModel):
    most_profitable_pair: str
    least_profitable_pair: str
    total_pl: float
    max_profit_trade: float
    max_loss_trade: float
    avg_profit_winner: float
    avg_loss_loser: float
    win_rate: float
    total_trades: int
    equity_curve: List[Dict[str, Any]]
