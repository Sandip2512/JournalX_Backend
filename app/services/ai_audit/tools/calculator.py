import pandas as pd
from typing import List, Dict
from app.services.ai_audit.contracts.schemas import (
    NormalizedTrade, PerformanceMetrics, SampleSizeCategory, SequenceMetrics,
    OvertradingMetrics, PositionSizeMetrics, AllAnalytics
)

def get_sample_size_cat(count: int) -> SampleSizeCategory:
    if count < 5: return SampleSizeCategory.VERY_SMALL
    if count < 20: return SampleSizeCategory.SMALL
    if count <= 50: return SampleSizeCategory.MODERATE
    return SampleSizeCategory.LARGE

def compute_metrics(trades: List[NormalizedTrade]) -> PerformanceMetrics:
    count = len(trades)
    ids = [t.trade_id for t in trades]
    
    if count == 0:
        return PerformanceMetrics(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0, net_pnl=0,
            average_win=0, average_loss=0, profit_factor=0, maximum_drawdown=0,
            sample_size_category=SampleSizeCategory.VERY_SMALL, trade_ids=ids
        )
        
    wins = [t for t in trades if t.net_profit > 0]
    losses = [t for t in trades if t.net_profit <= 0]
    
    win_len = len(wins)
    loss_len = len(losses)
    
    gross_profit = sum(t.net_profit for t in wins)
    gross_loss = abs(sum(t.net_profit for t in losses))
    net_pnl = gross_profit - gross_loss
    
    pf = 999.0 if gross_loss == 0 and gross_profit > 0 else (0.0 if gross_loss == 0 else gross_profit / gross_loss)
    
    # Calculate drawdown chronologically
    sorted_trades = sorted(trades, key=lambda x: x.close_timestamp)
    running_equity = 0.0
    peak = 0.0
    max_dd = 0.0
    for t in sorted_trades:
        running_equity += t.net_profit
        if running_equity > peak:
            peak = running_equity
        dd = peak - running_equity
        if dd > max_dd:
            max_dd = dd
            
    return PerformanceMetrics(
        total_trades=count,
        winning_trades=win_len,
        losing_trades=loss_len,
        win_rate=round(win_len / count * 100, 2),
        net_pnl=round(net_pnl, 2),
        average_win=round(gross_profit / win_len, 2) if win_len > 0 else 0.0,
        average_loss=round(gross_loss / loss_len, 2) if loss_len > 0 else 0.0,
        profit_factor=round(pf, 2),
        maximum_drawdown=round(max_dd, 2),
        sample_size_category=get_sample_size_cat(count),
        trade_ids=ids
    )

def analyze_sequences(trades: List[NormalizedTrade]) -> SequenceMetrics:
    sorted_trades = sorted(trades, key=lambda x: x.close_timestamp)
    
    after_loss_list = []
    after_win_list = []
    consecutive_loss_1 = []
    consecutive_loss_2 = []
    consecutive_loss_3_plus = []
    
    streak_losses = 0
    
    for i in range(1, len(sorted_trades)):
        prev = sorted_trades[i-1]
        curr = sorted_trades[i]
        
        if prev.net_profit <= 0:
            after_loss_list.append(curr)
            streak_losses += 1
            if streak_losses == 1: consecutive_loss_1.append(curr)
            elif streak_losses == 2: consecutive_loss_2.append(curr)
            else: consecutive_loss_3_plus.append(curr)
        else:
            after_win_list.append(curr)
            streak_losses = 0

    return SequenceMetrics(
        after_loss=compute_metrics(after_loss_list),
        after_win=compute_metrics(after_win_list),
        consecutive_losses_1=compute_metrics(consecutive_loss_1),
        consecutive_losses_2=compute_metrics(consecutive_loss_2),
        consecutive_losses_3_plus=compute_metrics(consecutive_loss_3_plus)
    )

def analyze_overtrading(trades: List[NormalizedTrade]) -> OvertradingMetrics:
    # Group by date using open_timestamp date
    by_day = {}
    for t in trades:
        # We need a robust day representation. Warning: Timezone might be naive.
        day_str = str(t.open_timestamp.date()) if t.open_timestamp else "UNKNOWN"
        if day_str not in by_day:
            by_day[day_str] = []
        by_day[day_str].append(t)
        
    t1_list, t2_list, t3_list, t4plus_list = [], [], [], []
    for day, day_trades in by_day.items():
        day_sorted = sorted(day_trades, key=lambda x: x.open_timestamp)
        for i, t in enumerate(day_sorted):
            if i == 0: t1_list.append(t)
            elif i == 1: t2_list.append(t)
            elif i == 2: t3_list.append(t)
            else: t4plus_list.append(t)
            
    return OvertradingMetrics(
        trade_1=compute_metrics(t1_list),
        trade_2=compute_metrics(t2_list),
        trade_3=compute_metrics(t3_list),
        trade_4_plus=compute_metrics(t4plus_list)
    )

def analyze_position_sizing(trades: List[NormalizedTrade]) -> PositionSizeMetrics:
    if not trades:
        return PositionSizeMetrics(average_volume=0.0, median_volume=0.0, volume_after_loss=0.0, volume_after_win=0.0, volume_during_drawdown=0.0, volume_groups={})
        
    vols = [t.volume for t in trades]
    vols.sort()
    avg_vol = sum(vols) / len(vols)
    mid = len(vols) // 2
    med_vol = (vols[mid] + vols[~mid]) / 2.0
    
    sorted_trades = sorted(trades, key=lambda x: x.close_timestamp)
    after_loss_vols = []
    after_win_vols = []
    drawdown_vols = []
    
    running_eq = 0.0
    peak = 0.0
    
    for i in range(len(sorted_trades)):
        curr = sorted_trades[i]
        
        # Sequent analytics
        if i > 0:
            prev = sorted_trades[i-1]
            if prev.net_profit <= 0: after_loss_vols.append(curr.volume)
            else: after_win_vols.append(curr.volume)
            
        # Drawdown logic
        if running_eq < peak:
            drawdown_vols.append(curr.volume)
            
        running_eq += curr.net_profit
        if running_eq > peak:
            peak = running_eq
            
    val = sum(after_loss_vols)/len(after_loss_vols) if after_loss_vols else 0.0
    vaw = sum(after_win_vols)/len(after_win_vols) if after_win_vols else 0.0
    vdd = sum(drawdown_vols)/len(drawdown_vols) if drawdown_vols else 0.0
    
    # groups (Under median, Over median)
    low_vol = [t for t in trades if t.volume <= med_vol]
    high_vol = [t for t in trades if t.volume > med_vol]
    
    return PositionSizeMetrics(
        average_volume=round(avg_vol, 2),
        median_volume=round(med_vol, 2),
        volume_after_loss=round(val, 2),
        volume_after_win=round(vaw, 2),
        volume_during_drawdown=round(vdd, 2),
        volume_groups={
            "LOW_VOLUME": compute_metrics(low_vol),
            "HIGH_VOLUME": compute_metrics(high_vol)
        }
    )

def extract_groups(trades: List[NormalizedTrade], key_extractor) -> Dict[str, PerformanceMetrics]:
    groups = {}
    for t in trades:
        k = key_extractor(t)
        if not k:
            k = "UNKNOWN"
        if k not in groups:
            groups[k] = []
        groups[k].append(t)
    
    result = {}
    for k, grp_trades in groups.items():
        result[k] = compute_metrics(grp_trades)
    return result

def holding_time_key(t: NormalizedTrade):
    if t.holding_time_minutes < 15: return "<15 minutes"
    if t.holding_time_minutes <= 60: return "15 minutes - 1 hour"
    return ">1 hour"

def full_analytics(trades: List[NormalizedTrade]) -> AllAnalytics:
    return AllAnalytics(
        base_metrics=compute_metrics(trades),
        sequence=analyze_sequences(trades),
        overtrading=analyze_overtrading(trades),
        position_sizing=analyze_position_sizing(trades),
        symbols=extract_groups(trades, lambda t: t.symbol),
        directions=extract_groups(trades, lambda t: t.direction),
        holding_times=extract_groups(trades, holding_time_key),
        days_of_week=extract_groups(trades, lambda t: t.open_timestamp.strftime("%A") if t.open_timestamp else "UNKNOWN")
    )
