from typing import List, Dict
import pandas as pd
from datetime import datetime
from app.services.ai_audit.schemas.ai_audit_schema import AgentTradeInput, DataAnalysisResult

def calculate_basic_metrics(trades: List[AgentTradeInput]) -> DataAnalysisResult:
    if not trades:
        return DataAnalysisResult(
            total_trades=0, win_rate=0.0, profit_factor=0.0,
            average_win=0.0, average_loss=0.0, net_profit=0.0,
            max_drawdown=0.0, largest_win=0.0, largest_loss=0.0
        )
        
    df = pd.DataFrame([t.model_dump() for t in trades])
    df = df.sort_values('close_time')
    
    total = len(df)
    wins = df[df['net_profit'] > 0]
    losses = df[df['net_profit'] <= 0]
    
    win_rate = (len(wins) / total * 100) if total > 0 else 0.0
    
    gross_profit = wins['net_profit'].sum()
    gross_loss = abs(losses['net_profit'].sum())
    
    profit_factor = round(gross_profit / gross_loss, 2) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)
    
    average_win = wins['net_profit'].mean() if len(wins) > 0 else 0.0
    average_loss = losses['net_profit'].mean() if len(losses) > 0 else 0.0
    
    largest_win = wins['net_profit'].max() if len(wins) > 0 else 0.0
    largest_loss = losses['net_profit'].min() if len(losses) > 0 else 0.0
    
    net_profit = df['net_profit'].sum()
    
    # Calculate Drawdown
    equity_curve = df['net_profit'].cumsum()
    peak = equity_curve.expanding(min_periods=1).max()
    drawdown = peak - equity_curve
    max_drawdown = drawdown.max()
    
    return DataAnalysisResult(
        total_trades=total,
        win_rate=round(win_rate, 2),
        profit_factor=profit_factor,
        average_win=round(float(average_win), 2),
        average_loss=round(float(average_loss), 2),
        net_profit=round(float(net_profit), 2),
        max_drawdown=round(float(max_drawdown), 2),
        largest_win=round(float(largest_win), 2),
        largest_loss=round(float(largest_loss), 2)
    )

def analyze_by_instrument(trades: List[AgentTradeInput]) -> Dict[str, dict]:
    df = pd.DataFrame([t.model_dump() for t in trades])
    if df.empty: return {}
    
    grouped = df.groupby('symbol')
    result = {}
    for symbol, group in grouped:
        wins = group[group['net_profit'] > 0]
        total = len(group)
        result[symbol] = {
            'count': total,
            'win_rate': round(len(wins) / total * 100, 2),
            'net_profit': round(group['net_profit'].sum(), 2),
            'profit_factor': round(
                wins['net_profit'].sum() / abs(group[group['net_profit'] <= 0]['net_profit'].sum()) 
                if abs(group[group['net_profit'] <= 0]['net_profit'].sum()) > 0 else 999.0, 2
            )
        }
    return result

def analyze_by_direction(trades: List[AgentTradeInput]) -> Dict[str, dict]:
    df = pd.DataFrame([t.model_dump() for t in trades])
    if df.empty: return {}
    
    grouped = df.groupby('type')
    result = {}
    for t_type, group in grouped:
        wins = group[group['net_profit'] > 0]
        total = len(group)
        result[t_type] = {
            'count': total,
            'win_rate': round(len(wins) / total * 100, 2),
            'net_profit': round(group['net_profit'].sum(), 2)
        }
    return result

def analyze_sequence(trades: List[AgentTradeInput]) -> dict:
    """Analyze behavior after a win vs after a loss."""
    df = pd.DataFrame([t.model_dump() for t in trades])
    if df.empty or len(df) < 2: return {}
    
    df = df.sort_values('close_time')
    # Create shift to see what the previous trade was
    df['prev_profit'] = df['net_profit'].shift(1)
    
    after_loss = df[df['prev_profit'] <= 0]
    after_win = df[df['prev_profit'] > 0]
    
    return {
        "after_loss": {
            "count": len(after_loss),
            "average_pl": round(after_loss['net_profit'].mean(), 2) if len(after_loss) > 0 else 0,
            "win_rate": round(len(after_loss[after_loss['net_profit'] > 0]) / len(after_loss) * 100, 2) if len(after_loss) > 0 else 0
        },
        "after_win": {
            "count": len(after_win),
            "average_pl": round(after_win['net_profit'].mean(), 2) if len(after_win) > 0 else 0,
            "win_rate": round(len(after_win[after_win['net_profit'] > 0]) / len(after_win) * 100, 2) if len(after_win) > 0 else 0
        }
    }
