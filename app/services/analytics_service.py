from pymongo.database import Database
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Simple in-memory cache: {user_id: {"data": data, "timestamp": timestamp}}
analytics_cache = {}
CACHE_DURATION_SECONDS = 300

def get_cached_analytics(user_id: str):
    if user_id in analytics_cache:
        entry = analytics_cache[user_id]
        if (datetime.now() - entry["timestamp"]).total_seconds() < CACHE_DURATION_SECONDS:
            return entry["data"]
    return None

def cache_analytics(user_id: str, data: Dict):
    analytics_cache[user_id] = {
        "data": data,
        "timestamp": datetime.now()
    }

def calculate_analytics(db: Database, user_id: str) -> Dict[str, Any]:
    print(f"DEBUG: calculate_analytics called for {user_id}")
    # Check cache
    cached = get_cached_analytics(user_id)
    if cached:
        print("DEBUG: Returning cached analytics")
        return cached

    print("DEBUG: Cache miss, fetching trades...")
    # Fetch all trades for user
    cursor = db.trades.find({"user_id": user_id}).sort("open_time", 1)
    trades = list(cursor)
    
    if not trades:
        return {
            "beginner": {
                "total_pl": 0.0,
                "win_rate": 0.0,
                "total_trades": 0,
                "avg_risk": 0.0,
                "equity_curve": []
            },
            "intermediate": {
                "strategy_performance": {},
                "day_of_week_performance": {},
                "avg_r": 0.0
            },
            "advanced": {
                "expectancy": 0.0,
                "max_drawdown": 0.0,
                "risk_consistency": 0.0,
                "mae_mfe": []
            }
        }

    # Convert to DataFrame for easier analysis
    data = []
    equity = 0.0
    equity_curve = []
    
    for t in trades:
        # Mongo dict access
        net = t.get("net_profit")
        if net is None:
            net = t.get("profit_amount", 0.0) - t.get("loss_amount", 0.0)
        equity += net
        
        # Calculate R-Multiple if not present
        r_mult = t.get("r_multiple")
        stop_loss = t.get("stop_loss", 0.0)
        price_open = t.get("price_open", 0.0)
        volume = t.get("volume", 0.0)
        symbol = t.get("symbol", "")
        
        if r_mult is None and stop_loss and stop_loss != 0 and price_open:
            risk = abs(price_open - stop_loss)
            if risk > 0:
                # Approx, strictly should use Tick Value.
                contract_size = 1000 if 'JPY' in symbol else 100000
                r_mult = net / (risk * (volume * contract_size)) 
                pass 

        data.append({
            "trade_no": t.get("trade_no"),  # Using trade_no instead of _id
            "net_profit": net,
            "win": 1 if net > 0 else 0,
            "loss": 1 if net <= 0 else 0,
            "strategy": t.get("strategy", "Unknown"),
            "type": t.get("type", "BUY"),
            "symbol": symbol,
            "day_of_week": t.get("open_time").strftime("%A") if t.get("open_time") else "Unknown",
            "equity": equity,
            "open_time": t.get("open_time"),
            "r_multiple": r_mult if r_mult is not None else 0.0,
            "mae": t.get("mae"),
            "mfe": t.get("mfe")
        })
        if t.get("open_time"):
            equity_curve.append({"time": t.get("open_time"), "equity": equity})

    df = pd.DataFrame(data)

    # --- Time-Based Analytics (For Goals) ---
    now = datetime.now()
    
    # Weekly Profit (Current Week)
    current_week = now.isocalendar()[1]
    current_year = now.year
    # Filter trades for current week & year
    # Note: open_time is datetime object in Mongo
    
    # Helper    # Calculate current week start (Sunday)
    curr_week_start = now - timedelta(days=(now.weekday() + 1) % 7)
    curr_week_start = curr_week_start.replace(hour=0, minute=0, second=0, microsecond=0)

    def is_current_week(dt):
        if not dt: return False
        # Normalize dt to date for comparison or check if it's after curr_week_start
        return dt >= curr_week_start

    def is_current_month(dt):
        if not dt: return False
        return dt.month == now.month and dt.year == now.year
        
    def is_current_year(dt):
        if not dt: return False
        return dt.year == now.year

    weekly_profit = sum(t["net_profit"] for t in data if is_current_week(t["open_time"]))
    monthly_profit = sum(t["net_profit"] for t in data if is_current_month(t["open_time"]))
    yearly_profit = sum(t["net_profit"] for t in data if is_current_year(t["open_time"]))

    def is_in_period(dt, days):
        if not dt: return False
        return dt >= (now - timedelta(days=days))

    three_month_profit = sum(t["net_profit"] for t in data if is_in_period(t["open_time"], 90))
    six_month_profit = sum(t["net_profit"] for t in data if is_in_period(t["open_time"], 180))

    # --- BEGINNER ---
    total_trades = len(df)
    total_pl = df['net_profit'].sum()
    win_rate = (df['win'].sum() / total_trades) * 100 if total_trades > 0 else 0
    avg_win = df[df['win'] == 1]['net_profit'].mean() if df['win'].sum() > 0 else 0
    avg_loss = df[df['loss'] == 1]['net_profit'].mean() if df['loss'].sum() > 0 else 0
    
    # Avg Risk
    avg_risk = abs(avg_loss) if avg_loss != 0 else 0

    starting_balance = 10000.0 # Default starting capital

    beginner = {
        "starting_balance": float(starting_balance),
        "total_pl": float(total_pl),
        "weekly_profit": float(weekly_profit),
        "monthly_profit": float(monthly_profit),
        "three_month_profit": float(three_month_profit),
        "six_month_profit": float(six_month_profit),
        "yearly_profit": float(yearly_profit),
        "win_rate": float(win_rate),
        "total_trades": int(total_trades),
        "avg_risk": float(avg_risk),
        "equity_curve": equity_curve  # Return full curve for frontend filtering
    }

    # --- Goal Achievement Check ---
    try:
        active_goals = list(db.goals.find({"user_id": user_id, "is_active": True}))
        for goal in active_goals:
            g_type = goal.get("goal_type")
            target = goal.get("target_amount", 0)
            
            if target <= 0: continue
            
            current_profit = 0
            if g_type == "weekly":
                current_profit = weekly_profit
            elif g_type == "monthly":
                current_profit = monthly_profit
            elif g_type == "yearly":
                current_profit = total_pl
                
            if current_profit >= target:
                db.goals.update_one(
                    {"_id": goal["_id"]},
                    {"$set": {
                        "achieved": True, 
                        "achieved_date": datetime.now(),
                        "final_amount": current_profit
                    }}
                )
    except Exception as e:
        print(f"Error checking goal achievement: {e}")

    # --- INTERMEDIATE ---
    # Strategy Performance
    strategy_perf = df.groupby('strategy')['net_profit'].sum().to_dict()
    
    # Day of Week
    day_perf = df.groupby('day_of_week')['net_profit'].sum().to_dict()
    
    # Avg R
    avg_r = df['r_multiple'].mean() if 'r_multiple' in df else 0.0

    # Long vs Short
    long_trades = df[df['type'].str.upper() == 'BUY'] if 'type' in df.columns else pd.DataFrame()
    short_trades = df[df['type'].str.upper() == 'SELL'] if 'type' in df.columns else pd.DataFrame()
    
    def get_dir_stats(dir_df):
        if dir_df.empty:
            return {"trades": 0, "pl": 0.0, "winRate": 0.0}
        dir_win_rate = (dir_df['win'].sum() / len(dir_df)) * 100
        return {
            "trades": int(len(dir_df)),
            "pl": float(dir_df['net_profit'].sum()),
            "winRate": float(dir_win_rate)
        }

    long_stats = get_dir_stats(long_trades)
    short_stats = get_dir_stats(short_trades)
    
    # Top Symbols
    symbol_perf = df.groupby('symbol').agg(
        trades=('net_profit', 'count'),
        pl=('net_profit', 'sum'),
        wins=('win', 'sum')
    )
    symbol_perf['winRate'] = (symbol_perf['wins'] / symbol_perf['trades']) * 100
    top_symbols = symbol_perf.sort_values('pl', ascending=False).head(5).reset_index().rename(columns={'symbol': 'name'}).to_dict('records')

    intermediate = {
        "strategy_performance": strategy_perf,
        "day_of_week_performance": day_perf,
        "long": long_stats,
        "short": short_stats,
        "top_symbols": top_symbols,
        "avg_r": float(avg_r)
    }

    # --- ADVANCED ---
    # Expectancy = (Win % * Avg Win) - (Loss % * Avg Loss)
    win_pct = win_rate / 100
    loss_pct = 1 - win_pct
    expectancy = (win_pct * avg_win) + (loss_pct * avg_loss)
    
    # Drawdown
    # Peak equity so far
    running_max = df['equity'].cummax()
    drawdown = df['equity'] - running_max
    max_drawdown = drawdown.min()

    # Risk Consistency (Std Dev of Risk/Loss)
    risk_consistency = df[df['loss'] == 1]['net_profit'].std() if df['loss'].sum() > 1 else 0

    advanced = {
        "expectancy": float(expectancy),
        "max_drawdown": float(max_drawdown),
        "risk_consistency": float(risk_consistency),
        # MAE/MFE scatter data would go here, limiting to last 50 trades
        "mae_mfe": df[['mae', 'mfe', 'net_profit']].fillna(0).tail(50).to_dict('records')
    }

    result = {
        "beginner": beginner,
        "intermediate": intermediate,
        "advanced": advanced
    }
    
    cache_analytics(user_id, result)
    return result

def get_calendar_stats(db: Database, user_id: str, month: int, year: int) -> List[Dict]:
    """Get daily P&L for a specific month/year"""
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
        
    query = {
        "user_id": user_id,
        "$or": [
            {"close_time": {"$gte": start_date, "$lt": end_date}},
            {"close_time": None, "open_time": {"$gte": start_date, "$lt": end_date}}
        ]
    }
    
    trades = list(db.trades.find(query))
    daily_stats = {}
    
    for t in trades:
        ref_time = t.get("close_time") or t.get("open_time")
        if not ref_time: continue
            
        day = ref_time.date().isoformat()
        if day not in daily_stats:
            daily_stats[day] = {"date": day, "profit": 0, "trades": 0}
        daily_stats[day]["profit"] += (t.get("net_profit") or 0)
        daily_stats[day]["trades"] += 1
        
    return list(daily_stats.values())

def get_weekly_review_stats(db: Database, user_id: str, start_date: datetime = None, end_date: datetime = None) -> Dict:
    """Get summary stats for a specific period"""
    if not end_date:
        end_date = datetime.now()
    if not start_date:
        start_date = end_date - timedelta(days=7)
    
    query = {
        "user_id": user_id,
        "$or": [
            {"close_time": {"$gte": start_date}},
            {"close_time": None, "open_time": {"$gte": start_date}}
        ]
    }
    
    trades = list(db.trades.find(query))
    
    if not trades:
        return {}
        
    df = pd.DataFrame([{
        "net_profit": t.get("net_profit") or 0,
        "symbol": t.get("symbol"),
        "mistake": t.get("mistake"),
        "ticket": t.get("trade_no")
    } for t in trades])
    
    best_trade = df.loc[df['net_profit'].idxmax()]
    worst_trade = df.loc[df['net_profit'].idxmin()]
    
    total_pl = df['net_profit'].sum()
    win_count = len(df[df['net_profit'] > 0])
    # loss_count = len(df[df['net_profit'] <= 0])
    
    # Biggest mistake count
    mistake_counts = df[df['mistake'] != 'No Mistake']['mistake'].value_counts()
    top_mistake = mistake_counts.index[0] if not mistake_counts.empty else "None"
    
    return {
        "period": f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
        "total_pl": float(total_pl),
        "total_trades": len(df),
        "win_rate": float((win_count / len(df)) * 100),
        "best_trade": {"symbol": best_trade['symbol'], "profit": float(best_trade['net_profit'])},
        "worst_trade": {"symbol": worst_trade['symbol'], "profit": float(worst_trade['net_profit'])},
        "top_mistake": top_mistake
    }

def generate_insights(db: Database, user_id: str) -> List[Dict]:
    """Generate smart text-based insights"""
    # Look back 30 days for relevance
    start_date = datetime.now() - timedelta(days=30)
    
    query = {
        "user_id": user_id, 
        "$or": [
            {"close_time": {"$gte": start_date}},
            {"close_time": None, "open_time": {"$gte": start_date}}
        ]
    }
    
    trades = list(db.trades.find(query))
    
    if len(trades) < 5:
        return [{"type": "info", "text": "Keep trading! Insights appear after 5+ trades."}]
        
    df = pd.DataFrame([{
        "net_profit": t.get("net_profit") or 0,
        "hour": t.get("open_time").hour if t.get("open_time") else 0,
        "day": t.get("open_time").strftime("%A") if t.get("open_time") else "Unknown",
        "type": t.get("type"),
        "result": "win" if (t.get("net_profit") or 0) > 0 else "loss"
    } for t in trades])
    
    insights = []
    
    # 1. Day Analysis
    day_perf = df.groupby('day')['net_profit'].sum()
    if not day_perf.empty:
        best_day = day_perf.idxmax()
        worst_day = day_perf.idxmin()
        if day_perf[best_day] > 0:
            insights.append({"type": "good", "text": f"You are most profitable on {best_day}s."})
        if day_perf[worst_day] < 0:
            insights.append({"type": "warning", "text": f"{worst_day}s are currently your worst performing days."})
            
    # 2. Time Analysis (Asian/London/NY rough proxy)
    # < 8: Asia, 8-16: London/Pre-NY, > 16: NY/Close
    # Simple hour check
    df['session'] = pd.cut(df['hour'], bins=[0, 7, 15, 24], labels=['Asia', 'London', 'New York'], include_lowest=True)
    session_perf = df.groupby('session', observed=True)['net_profit'].mean()
    if not session_perf.empty:
        best_session = session_perf.idxmax()
        try:
            insights.append({"type": "info", "text": f"Your trades in {best_session} session have the highest average return."})
        except:
             pass # Handle if best_session is NaN
        
    # 3. Long vs Short
    type_perf = df.groupby('type')['net_profit'].sum()
    if 'BUY' in type_perf and 'SELL' in type_perf: # type is usually case insensitive in dict, check data
         # Assuming 'buy'/'sell' or 'BUY'/'SELL'
         pass 

    return insights[:4] # Return max 4 insights


def get_diary_stats(db: Database, user_id: str, start_date: datetime, end_date: datetime) -> Dict:
    """
    Get comprehensive diary stats:
    - Streaks (Current, Longest in period)
    - Days Traded, Profitable Days
    - Period Max Profit vs All Time Max Profit
    - Calendar Grid Data
    """
    
    # 1. Fetch ALL trades for streaks and all-time calculation
    all_trades = list(db.trades.find({"user_id": user_id}))
    
    # Process all trades into daily P&L
    daily_pnl = {}
    
    most_profitable_all_time = {"profit": 0, "date": None}
    
    for t in all_trades:
        ref_time = t.get("close_time") or t.get("open_time")
        if not ref_time: continue
            
        date_str = ref_time.date().isoformat()
        
        net_profit = t.get("net_profit") or 0
        
        # All Time Best Trade Check
        if net_profit > most_profitable_all_time["profit"]:
             most_profitable_all_time = {
                 "profit": net_profit,
                 "date": date_str
             }

        if date_str not in daily_pnl:
            daily_pnl[date_str] = {"profit": 0, "trades": 0, "date": date_str}
        
        daily_pnl[date_str]["profit"] += net_profit
        daily_pnl[date_str]["trades"] += 1
        
    # Sort dates
    sorted_dates = sorted(daily_pnl.keys())
    
    # Calculate Current Streak (working backwards from today)
    current_streak = 0
    today_str = datetime.now().date().isoformat()
    
    # Find index of last traded day <= today
    last_idx = -1
    for i, d in enumerate(sorted_dates):
        if d <= today_str:
            last_idx = i
        else:
            break
            
    if last_idx != -1:
        # Check if the last traded day was profitable
        curr_idx = last_idx
        while curr_idx >= 0:
            date_key = sorted_dates[curr_idx]
            if daily_pnl[date_key]["profit"] > 0:
                current_streak += 1
                curr_idx -= 1
            else:
                break
    
    # Filter for selected period
    period_days = []
    total_period_pl = 0
    period_trades_count = 0
    most_profitable_period = {"profit": 0, "date": None}
    winning_streak_period = 0
    current_period_streak = 0
    
    in_profit_days = 0
    traded_on_days = 0
    
    s_date = start_date.date()
    e_date = end_date.date()
    
    # Recalculate Period Stats
    for date_key in sorted_dates:
        d_obj = datetime.strptime(date_key, "%Y-%m-%d").date()
        if s_date <= d_obj <= e_date:
            day_data = daily_pnl[date_key]
            period_days.append(day_data)
            
            total_period_pl += day_data["profit"]
            period_trades_count += day_data["trades"]
            traded_on_days += 1
            
            if day_data["profit"] > 0:
                in_profit_days += 1
                current_period_streak += 1
                if day_data["profit"] > most_profitable_period["profit"]:
                    most_profitable_period = {
                        "profit": day_data["profit"],
                        "date": date_key
                    }
            else:
                current_period_streak = 0
            
            winning_streak_period = max(winning_streak_period, current_period_streak)

    # 3. Trades List for the period (Detailed)
    detailed_trades = []
    for t in all_trades:
        ref_time = t.get("close_time") or t.get("open_time")
        if ref_time:
             if s_date <= ref_time.date() <= e_date:
                 detailed_trades.append({
                     "id": t.get("trade_no"), # Use trade_no as visible ID
                     "trade_no": t.get("trade_no"),
                     "name": f"{t.get('symbol')}", 
                     "date": ref_time.strftime("%b %d"),
                     "iso_date": ref_time.date().isoformat(),
                     "result": "Win" if (t.get("net_profit") or 0) > 0 else "Loss",
                     "net_profit": t.get("net_profit") or 0,
                     "mistake": t.get("mistake")
                 })
    
    detailed_trades.sort(key=lambda x: x["trade_no"] if x["trade_no"] else 0, reverse=True)
    
    return {
        "net_pl": total_period_pl,
        "most_profitable_period": most_profitable_period,
        "most_profitable_all_time": most_profitable_all_time,
        "trading_days": (e_date - s_date).days + 1,
        "traded_on": traded_on_days,
        "in_profit_days": in_profit_days,
        "winning_streak": winning_streak_period,
        "current_streak": current_streak,
        "grid_data": period_days,
        "trades_list": detailed_trades
    }

