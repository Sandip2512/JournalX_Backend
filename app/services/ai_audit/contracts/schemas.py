from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any
from datetime import datetime
from enum import Enum

class DataQualityStatus(str, Enum):
    VALID = "VALID"
    WARNING = "WARNING"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    INVALID = "INVALID"

class NormalizedTrade(BaseModel):
    trade_id: str
    open_timestamp: datetime
    close_timestamp: datetime
    holding_time_minutes: float
    symbol: str
    direction: str
    volume: float
    open_price: float
    close_price: float
    net_profit: float
    
    session: Optional[str] = None
    strategy: Optional[str] = None
    emotion: Optional[str] = None
    mistake: Optional[str] = None
    reason: Optional[str] = None

class DataQualityResult(BaseModel):
    status: DataQualityStatus
    warnings: List[str]
    valid_trades: List[NormalizedTrade]

class SampleSizeCategory(str, Enum):
    VERY_SMALL = "VERY_SMALL"
    SMALL = "SMALL"
    MODERATE = "MODERATE"
    LARGE = "LARGE"

class PerformanceMetrics(BaseModel):
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_pnl: float
    average_win: float
    average_loss: float
    profit_factor: float
    maximum_drawdown: float
    sample_size_category: SampleSizeCategory
    trade_ids: List[str] = [] # Evidence tracking

class GroupComparison(BaseModel):
    group_name: str
    metrics: PerformanceMetrics

class SequenceMetrics(BaseModel):
    after_loss: PerformanceMetrics
    after_win: PerformanceMetrics
    consecutive_losses_1: PerformanceMetrics
    consecutive_losses_2: PerformanceMetrics
    consecutive_losses_3_plus: PerformanceMetrics

class OvertradingMetrics(BaseModel):
    trade_1: PerformanceMetrics
    trade_2: PerformanceMetrics
    trade_3: PerformanceMetrics
    trade_4_plus: PerformanceMetrics

class PositionSizeMetrics(BaseModel):
    average_volume: float
    median_volume: float
    volume_after_loss: float
    volume_after_win: float
    volume_during_drawdown: float
    volume_groups: Dict[str, PerformanceMetrics]

class AllAnalytics(BaseModel):
    base_metrics: PerformanceMetrics
    sequence: SequenceMetrics
    overtrading: OvertradingMetrics
    position_sizing: PositionSizeMetrics
    symbols: Dict[str, PerformanceMetrics]
    directions: Dict[str, PerformanceMetrics]
    holding_times: Dict[str, PerformanceMetrics]
    days_of_week: Dict[str, PerformanceMetrics]
