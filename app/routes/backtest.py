from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.database import Database
from typing import List
from app.mongo_database import get_db
from app.schemas.backtest_schema import (
    BacktestSession, BacktestSessionCreate,
    BacktestTrade, BacktestTradeCreate,
    BacktestStats
)
from app.crud.backtest_crud import (
    create_backtest_session, get_backtest_sessions, get_backtest_session,
    create_backtest_trade, get_session_trades, update_backtest_trade,
    calculate_session_stats, delete_backtest_session
)
from app.routes.auth import get_current_user

router = APIRouter()

def check_elite_access(user: dict):
    if user.get("subscription_tier") != "elite":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Backtesting is exclusively available for Elite members."
        )

@router.post("/sessions", response_model=BacktestSession)
async def create_session(
    session: BacktestSessionCreate, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    session_data = session.model_dump()
    session_data["user_id"] = current_user["user_id"]
    return create_backtest_session(db, session_data)

@router.get("/sessions", response_model=List[BacktestSession])
async def list_sessions(
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    return get_backtest_sessions(db, current_user["user_id"])

@router.get("/sessions/{session_id}", response_model=BacktestSession)
async def get_session(
    session_id: str, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    session = get_backtest_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=403, detail="Unauthorized access")
    return session

@router.post("/trades", response_model=BacktestTrade)
async def record_trade(
    trade: BacktestTradeCreate, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    trade_data = trade.model_dump()
    trade_data["user_id"] = current_user["user_id"]
    return create_backtest_trade(db, trade_data)

@router.get("/sessions/{session_id}/trades", response_model=List[BacktestTrade])
async def get_trades(
    session_id: str, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    # Security check: ensure session belongs to user
    session = get_backtest_session(db, session_id)
    if not session or session["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
    return get_session_trades(db, session_id)

@router.patch("/trades/{trade_id}", response_model=BacktestTrade)
async def update_trade(
    trade_id: str, 
    update_data: dict, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    # Note: CRUD should ideally check ownership or we do it here
    trade = update_backtest_trade(db, trade_id, update_data)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade

@router.get("/sessions/{session_id}/stats", response_model=BacktestStats)
async def get_stats(
    session_id: str, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    stats = calculate_session_stats(db, session_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats

@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str, 
    current_user: dict = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    check_elite_access(current_user)
    # Check ownership
    session = get_backtest_session(db, session_id)
    if not session or session["user_id"] != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Session not found")
        
    success = delete_backtest_session(db, session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"status": "success", "message": "Session deleted"}
