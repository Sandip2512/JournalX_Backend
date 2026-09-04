from fastapi import APIRouter, Depends, HTTPException, Query
from pymongo.database import Database
from typing import List, Optional
from datetime import datetime, date
from app.mongo_database import get_db
from app.routes.admin import get_current_user_role
from pydantic import BaseModel

router = APIRouter()

# --- Schemas ---
class TradeEditRequest(BaseModel):
    mistake: Optional[str] = None
    reason: Optional[str] = None
    profit_amount: Optional[float] = None
    loss_amount: Optional[float] = None
    # Add other editable fields as needed

# --- Endpoints ---
@router.get("/")
def get_all_trades(
    user_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    query = {}
    
    if user_id:
        query["user_id"] = user_id
        
    if start_date or end_date:
        query["close_time"] = {}
        # Convert date to datetime for comparison if needed, or rely on format
        # Pymongo stores datetime.
        if start_date:
            query["close_time"]["$gte"] = datetime.combine(start_date, datetime.min.time())
        if end_date:
            query["close_time"]["$lte"] = datetime.combine(end_date, datetime.max.time())
        if not query["close_time"]: del query["close_time"]

    cursor = db.trades.find(query).sort("close_time", -1).skip(skip).limit(limit)
    trades = list(cursor)
    count = db.trades.count_documents(query)
    
    # clean _id
    for t in trades:
        t["id"] = t.get("trade_no") # Use trade_no as ID for frontend display often
        t.pop("_id", None)
        
    return {"trades": trades, "total": count}

@router.put("/{trade_id}")
def update_trade(
    trade_id: int,
    trade_update: TradeEditRequest,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    # Find trade by trade_no (assuming trade_id in URL is trade_no, which is int)
    trade = db.trades.find_one({"trade_no": trade_id})
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    update_data = {}
    if trade_update.mistake is not None: update_data["mistake"] = trade_update.mistake
    if trade_update.reason is not None: update_data["reason"] = trade_update.reason
    if trade_update.profit_amount is not None: update_data["profit_amount"] = trade_update.profit_amount
    if trade_update.loss_amount is not None: update_data["loss_amount"] = trade_update.loss_amount
    
    # Recalculate net profit if needed
    current_profit = update_data.get("profit_amount", trade.get("profit_amount", 0))
    current_loss = update_data.get("loss_amount", trade.get("loss_amount", 0))
    
    if current_profit != 0 or current_loss != 0:
        update_data["net_profit"] = current_profit - current_loss
        
    if update_data:
        db.trades.update_one({"trade_no": trade_id}, {"$set": update_data})
        # return updated
        trade = db.trades.find_one({"trade_no": trade_id})
        
    trade.pop("_id", None)
    return trade

@router.delete("/{trade_id}")
def delete_trade(
    trade_id: int,
    db: Database = Depends(get_db),
    admin: dict = Depends(get_current_user_role)
):
    if admin.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
        
    result = db.trades.delete_one({"trade_no": trade_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Trade not found")
        
    return {"message": "Trade deleted successfully"}
