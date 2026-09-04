from pydantic import BaseModel
from typing import List, Dict, Optional
from datetime import datetime
from enum import Enum

class AgentTradeInput(BaseModel):
    trade_no: Optional[int] = None
    ticket: Optional[str] = None
    symbol: str
    volume: float
    type: str  # 'BUY' or 'SELL'
    price_open: float
    price_close: float
    net_profit: float
    open_time: datetime
    close_time: datetime
    
    # Optional / Manual
    reason: Optional[str] = None
    mistake: Optional[str] = None
    session: Optional[str] = None
    duration_minutes: Optional[float] = None

class DataAnalysisResult(BaseModel):
    total_trades: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    net_profit: float
    max_drawdown: float
    largest_win: float
    largest_loss: float

class VerificationStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    SUPPORTED = "SUPPORTED"
    QUESTIONABLE = "QUESTIONABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECTED = "REJECTED"

class CandidateFinding(BaseModel):
    category: str         
    claim: str            
    severity: str         
    evidence_stats: dict  

class BehaviorFinding(CandidateFinding):
    pass

class VerifiedFinding(BaseModel):
    category: str
    title: str
    claim: str
    severity: str 
    verification_status: VerificationStatus
    evidence: str          
    sample_size: int       
    confidence: str        
    explanation: str       

class AuditReport(BaseModel):
    overall_score: int
    analyzed_trades_count: int
    data_summary: DataAnalysisResult
    critical_findings: List[VerifiedFinding]
    positive_patterns: List[VerifiedFinding]
    negative_patterns: List[VerifiedFinding]
    behavior_findings: List[VerifiedFinding]
    recommendations: List[str]
