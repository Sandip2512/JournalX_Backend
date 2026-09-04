from pymongo.database import Database
import pymongo
from datetime import datetime
import uuid
from typing import List, Optional

def create_backtest_session(db: Database, session_data: dict):
    session_id = str(uuid.uuid4())
    session_data["_id"] = session_id
    session_data["created_at"] = datetime.now()
    session_data["status"] = "active"
    
    db.backtest_sessions.insert_one(session_data)
    return session_data

def get_backtest_sessions(db: Database, user_id: str):
    cursor = db.backtest_sessions.find({"user_id": user_id}).sort("created_at", pymongo.DESCENDING)
    sessions = list(cursor)
    return sessions

def get_backtest_session(db: Database, session_id: str):
    return db.backtest_sessions.find_one({"_id": session_id})

def create_backtest_trade(db: Database, trade_data: dict):
    trade_id = str(uuid.uuid4())
    trade_data["_id"] = trade_id
    
    # Calculate profit/loss if it's already closed
    if trade_data.get("status") == "closed" and trade_data.get("exit_price"):
        trade_data["profit_loss"] = calculate_backtest_pl(trade_data)
    
    db.backtest_trades.insert_one(trade_data)
    return trade_data

def get_session_trades(db: Database, session_id: str):
    cursor = db.backtest_trades.find({"session_id": session_id}).sort("entry_time", pymongo.ASCENDING)
    return list(cursor)

def update_backtest_trade(db: Database, trade_id: str, update_data: dict):
    # If closing, calculate PL
    if update_data.get("status") == "closed":
        trade = db.backtest_trades.find_one({"_id": trade_id})
        if trade:
            # Merge existing trade with update data for calculation
            temp_trade = {**trade, **update_data}
            update_data["profit_loss"] = calculate_backtest_pl(temp_trade)
            update_data["exit_time"] = update_data.get("exit_time", datetime.now())

    db.backtest_trades.update_one({"_id": trade_id}, {"$set": update_data})
    return db.backtest_trades.find_one({"_id": trade_id})

def calculate_backtest_pl(trade: dict):
    entry = trade["entry_price"]
    exit = trade["exit_price"]
    lot_size = trade["lot_size"]
    trade_type = trade["trade_type"].lower()
    
    # Simple calculation: (Exit - Entry) * LotSize * multiplier
    # Assuming standard Forex lot size (100,000 unit) for simplicity or direct dollar calculation
    # For now, let's treat lot_size as a simple multiplier for the price difference
    if trade_type == "buy":
        return (exit - entry) * lot_size
    else:
        return (entry - exit) * lot_size

def calculate_session_stats(db: Database, session_id: str):
    trades = get_session_trades(db, session_id)
    session = get_backtest_session(db, session_id)
    
    if not session:
        return None
        
    total_trades = len(trades)
    if total_trades == 0:
        return {
            "session_id": session_id,
            "total_trades": 0,
            "win_rate": 0,
            "net_pnl": 0,
            "max_drawdown": 0,
            "avg_rr": 0,
            "equity_curve": [{"timestamp": session["created_at"], "equity": session["starting_balance"]}]
        }
    
    wins = len([t for t in trades if t.get("profit_loss", 0) > 0])
    win_rate = (wins / total_trades) * 100
    net_pnl = sum([t.get("profit_loss", 0) for t in trades])
    
    # Calculate equity curve and drawdown
    equity = session["starting_balance"]
    equity_curve = [{"timestamp": session["created_at"], "equity": equity}]
    max_equity = equity
    max_dd = 0
    
    for t in trades:
        pl = t.get("profit_loss", 0)
        equity += pl
        equity_curve.append({"timestamp": t.get("exit_time") or t.get("entry_time"), "equity": equity})
        
        if equity > max_equity:
            max_equity = equity
        
        dd = (max_equity - equity) / max_equity * 100 if max_equity > 0 else 0
        if dd > max_dd:
            max_dd = dd
            
    return {
        "session_id": session_id,
        "total_trades": total_trades,
        "win_rate": round(win_rate, 2),
        "net_pnl": round(net_pnl, 2),
        "max_drawdown": round(max_dd, 2),
        "avg_rr": 0, # Placeholder for more complex calc
        "equity_curve": equity_curve
    }
def delete_backtest_session(db: Database, session_id: str):
    # Delete all trades in this session
    db.backtest_trades.delete_many({"session_id": session_id})
    # Delete the session
    result = db.backtest_sessions.delete_one({"_id": session_id})
    return result.deleted_count > 0
