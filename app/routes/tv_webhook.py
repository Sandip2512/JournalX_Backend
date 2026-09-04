from fastapi import APIRouter, Depends, HTTPException, Body, Request
from pymongo.database import Database
from app.mongo_database import get_db
from app.crud.trade_crud import create_trade, get_trades, update_trade
from app.crud.backtest_crud import create_backtest_trade, update_backtest_trade
from app.crud.user_crud import get_all_users
from datetime import datetime
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def tradingview_webhook(
    request: Request,
    db: Database = Depends(get_db),
    payload: dict = Body(...)
):
    """
    Handle incoming alerts from TradingView.
    Expected Payload:
    {
        "ticker": "XAUUSD",
        "action": "buy" | "sell" | "close",
        "price": 2350.50,
        "volume": 0.1,
        "token": "YOUR_SECRET_TOKEN",
        "comment": "Optional comment"
    }
    """
    token = payload.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="Webhook token missing")

    # Find user by webhook token
    user = db.users.find_one({"tv_webhook_token": token})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid webhook token")

    user_id = user["user_id"]
    action = payload.get("action", "").lower()
    ticker = payload.get("ticker", "Unknown")
    price = payload.get("price", 0.0)
    volume = payload.get("volume", 0.01)
    comment = payload.get("comment", "TradingView Alert")

    if action in ["buy", "sell"]:
        # NEW: Check for active backtesting session of mode 'tv_sync'
        active_session = db.backtest_sessions.find_one({
            "user_id": user_id,
            "mode": "tv_sync",
            "status": "active"
        })

        if active_session:
            # Route to backtesting session
            new_trade = {
                "session_id": active_session["_id"],
                "pair": ticker,
                "trade_type": action.upper(),
                "entry_price": price,
                "entry_time": datetime.now().isoformat(),
                "lot_size": volume,
                "status": "open",
                "notes": f"TV Sync: {comment}"
            }
            created = create_backtest_trade(db, new_trade)
            logger.info(f"TV Sync trade routed to BT Session for {user['email']}: {ticker}")
            return {"status": "success", "message": "Trade opened in Backtest session", "trade": created}

        # Original logic: Create new normal trade
        new_trade = {
            "user_id": user_id,
            "pair": ticker,
            "trade_type": action.upper(),
            "entry_price": price,
            "entry_time": datetime.now().isoformat(),
            "lot_size": volume,
            "status": "open",
            "reason": comment,
            "tags": ["TradingView", "Automated"]
        }
        created = create_trade(db, new_trade)
        logger.info(f"Automated trade created for {user['email']}: {ticker} {action}")
        return {"status": "success", "message": "Trade opened", "trade": created}

    elif action == "close":
        # NEW: Check for active backtesting session of mode 'tv_sync'
        active_session = db.backtest_sessions.find_one({
            "user_id": user_id,
            "mode": "tv_sync",
            "status": "active"
        })

        if active_session:
            open_trades = list(db.backtest_trades.find({
                "session_id": active_session["_id"],
                "pair": ticker,
                "status": "open"
            }).sort("entry_time", -1).limit(1))

            if open_trades:
                target_trade = open_trades[0]
                update_data = {
                    "exit_price": price,
                    "exit_time": datetime.now().isoformat(),
                    "status": "closed"
                }
                updated = update_backtest_trade(db, target_trade["_id"], update_data)
                logger.info(f"TV Sync trade CLOSED in BT Session for {user['email']}: {ticker}")
                return {"status": "success", "message": "Trade closed in Backtest session", "trade": updated}

        # Original logic: Find the most recent open trade for this ticker
        open_trades = list(db.trades.find({
            "user_id": user_id,
            "pair": ticker,
            "status": "open"
        }).sort("entry_time", -1).limit(1))

        if not open_trades:
            return {"status": "error", "message": f"No open trade found for {ticker} to close"}

        target_trade = open_trades[0]
        update_data = {
            "exit_price": price,
            "exit_time": datetime.now().isoformat(),
            "status": "closed"
        }
        
        # Calculate profit/loss
        entry_price = target_trade["entry_price"]
        lot_size = target_trade["lot_size"]
        if target_trade["trade_type"] == "BUY":
            pnl = (price - entry_price) * lot_size
        else:
            pnl = (entry_price - price) * lot_size
            
        update_data["profit_loss"] = pnl
        update_data["net_profit"] = pnl

        updated = update_trade(db, target_trade["trade_no"], update_data)
        logger.info(f"Automated trade closed for {user['email']}: {ticker}")
        return {"status": "success", "message": "Trade closed", "trade": updated}

    else:
        return {"status": "error", "message": "Invalid action. Use 'buy', 'sell', or 'close'"}
