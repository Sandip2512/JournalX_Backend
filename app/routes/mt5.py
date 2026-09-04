from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pymongo.database import Database
from typing import List, Optional
from slowapi import Limiter
from slowapi.util import get_remote_address
import logging

from app.mongo_database import get_db
from app.services.mt5_service import fetch_mt5_trades
from app.crud.mt5_crud import (
    create_mt5_credentials, get_mt5_credentials,
    update_mt5_credentials, delete_mt5_credentials,
    create_or_refresh_token, get_mt5_connection,
    get_user_by_token, update_last_sync, delete_mt5_connection
)
from app.crud.trade_crud import create_trade, get_trade_by_ticket
from app.schemas.mt5_schema import (
    MT5CredentialsCreate, MT5CredentialsResponse,
    MT5TokenRequest, MT5TokenResponse, MT5EASyncPayload, MT5ConnectionStatus
)
from app.services.mt5_service import calculate_profit_loss, normalize_symbol

logger = logging.getLogger(__name__)
router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


# ══════════════════════════════════════════════════════════════════════════════
# EA / TOKEN-BASED ENDPOINTS  (new — EA bridge)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/generate-token", response_model=dict)
async def generate_connection_token(request: MT5TokenRequest, db: Database = Depends(get_db)):
    """
    Generate a secure connection token for the user.
    The user enters this token into the JournalX EA in MT5.
    The user's MT5 credentials (account ID, password, server) are entered
    directly into the EA inputs and stay on their machine — never sent here.
    """
    try:
        from app.crud.user_crud import get_user_by_id
        user = get_user_by_id(db, request.user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        record = create_or_refresh_token(db, request.user_id)
        logger.info(f"✅ Token generated for user {request.user_id}")
        return {
            "token": record["token"],
            "user_id": request.user_id,
            "created_at": record["created_at"].isoformat(),
            "message": "Token generated. Enter this in the JournalX EA inputs in MetaTrader 5."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Token generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/ea/sync", response_model=dict)
@limiter.limit("30/minute")
async def ea_sync_trades(
    request: Request,
    payload: MT5EASyncPayload,
    authorization: Optional[str] = Header(None),
    db: Database = Depends(get_db)
):
    """
    The MT5 EA calls this endpoint to push closed trades.
    Authentication: Bearer token in Authorization header.
    The EA sends: symbol, type, volume, open/close prices, net P/L, timestamps.
    The user's MT5 credentials are NEVER sent here — they stay on the user's machine.

    Upsert logic:
      - If a trade with the same mt5_ticket already exists → update it (handles
        open→closed transitions and reconnect after offline).
      - If it's new → insert it.
    """
    # ── Token auth ─────────────────────────────────────────────────────────
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid Authorization header")

    token = authorization.removeprefix("Bearer ").strip()
    user_id = get_user_by_token(db, token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid connection token")

    # Lookup active account to auto-tag these trades
    from app.crud.mt5_crud import get_mt5_credentials
    mt5_creds = get_mt5_credentials(db, user_id)
    active_account = str(mt5_creds["account"]) if mt5_creds and mt5_creds.get("account") else None

    # ── Upsert trades ───────────────────────────────────────────────────────
    synced = 0
    updated = 0
    skipped = 0

    for trade_item in payload.trades:
        try:
            # Check if this MT5 ticket is already in our DB
            existing = db.trades.find_one({"mt5_ticket": trade_item.mt5_ticket, "user_id": user_id})

            profit_amount, loss_amount = calculate_profit_loss(trade_item.net_profit)

            trade_data = {
                "user_id": user_id,
                "mt5_ticket": trade_item.mt5_ticket,
                "symbol": normalize_symbol(trade_item.symbol),
                "type": trade_item.type,
                "volume": trade_item.volume,
                "price_open": trade_item.price_open,
                "price_close": trade_item.price_close,
                "net_profit": trade_item.net_profit,
                "profit_amount": profit_amount,
                "loss_amount": loss_amount,
                "open_time": trade_item.open_time,
                "close_time": trade_item.close_time,
                "reason": "MT5 EA Sync",
                "take_profit": 0.0,
                "stop_loss": 0.0
            }
            if active_account:
                trade_data["mt5_account"] = active_account

            if existing:
                # Update fields that may have changed (e.g. close price / P&L after close)
                db.trades.update_one(
                    {"mt5_ticket": trade_item.mt5_ticket, "user_id": user_id},
                    {"$set": {
                        "price_close": trade_item.price_close,
                        "net_profit": trade_item.net_profit,
                        "profit_amount": profit_amount,
                        "loss_amount": loss_amount,
                        "close_time": trade_item.close_time,
                    }}
                )
                updated += 1
            else:
                # Insert new trade (create_trade auto-assigns trade_no)
                create_trade(db, trade_data)
                synced += 1

        except Exception as e:
            logger.warning(f"Error syncing ticket {trade_item.mt5_ticket}: {e}")
            skipped += 1

    # Stamp last sync time
    update_last_sync(db, user_id)

    logger.info(f"EA sync for user {user_id}: +{synced} new, {updated} updated, {skipped} skipped")
    return {
        "status": "ok",
        "synced": synced,
        "updated": updated,
        "skipped": skipped,
        "total_received": len(payload.trades)
    }


@router.get("/connection-status", response_model=dict)
async def get_connection_status(user_id: str, db: Database = Depends(get_db)):
    """
    Returns whether the user has an active EA connection and sync stats.
    """
    try:
        record = get_mt5_connection(db, user_id)
        if not record:
            return {
                "connected": False,
                "token_preview": None,
                "last_sync_at": None,
                "synced_trades_count": 0
            }

        # Count trades already synced via EA
        count = db.trades.count_documents({"user_id": user_id, "reason": "MT5 EA Sync"})
        token = record.get("token", "")

        return {
            "connected": True,
            "token_preview": token[:8] + "..." if token else None,
            "last_sync_at": record.get("last_sync_at").isoformat() if record.get("last_sync_at") else None,
            "synced_trades_count": count
        }
    except Exception as e:
        logger.error(f"Connection status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/token", response_model=dict)
async def disconnect_ea(user_id: str, db: Database = Depends(get_db)):
    """
    Revoke the connection token and disconnect the EA.
    """
    try:
        deleted = delete_mt5_connection(db, user_id)
        if deleted:
            return {"status": "disconnected", "message": "EA connection removed. The EA will stop syncing."}
        return {"status": "not_found", "message": "No active EA connection found"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ══════════════════════════════════════════════════════════════════════════════
# CREDENTIAL-BASED ENDPOINTS  (existing — unchanged)
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/connect", response_model=dict)
async def connect_mt5(credentials: MT5CredentialsCreate, db: Database = Depends(get_db)):
    """
    Connect to MT5 and store/update credentials (legacy credential-based approach).
    """
    try:
        print(f"🔌 MT5 Connection attempt:")
        print(f"   Account: {credentials.account}")
        print(f"   Server: {credentials.server}")
        print(f"   User ID: {credentials.user_id}")
        print(f"   Days: {credentials.days}")

        if not credentials.account:
            raise HTTPException(status_code=400, detail="Account number is required")
        if not credentials.password:
            raise HTTPException(status_code=400, detail="Password is required")
        if not credentials.server:
            raise HTTPException(status_code=400, detail="Server is required")
        if not credentials.user_id:
            raise HTTPException(status_code=400, detail="User ID is required")

        from app.crud.user_crud import get_user_by_id
        user = get_user_by_id(db, credentials.user_id)
        if not user:
            raise HTTPException(status_code=404, detail=f"User with ID {credentials.user_id} not found.")

        try:
            trades = fetch_mt5_trades(
                account=credentials.account,
                password=credentials.password,
                server=credentials.server,
                days=credentials.days
            )
            print(f"✅ MT5 Connection successful, found {len(trades) if trades else 0} trades")
        except Exception as mt5_error:
            error_msg = str(mt5_error)
            print(f"❌ MT5 connection error: {error_msg}")
            if "disconnected" in error_msg.lower() or "connection lost" in error_msg.lower():
                raise HTTPException(status_code=503, detail="MT5 account disconnected from broker server.")
            elif "IPC timeout" in error_msg or "(-10005" in error_msg:
                raise HTTPException(status_code=503, detail="MT5 terminal is not responding (IPC timeout).")
            elif "Authorization failed" in error_msg or "(-6" in error_msg:
                raise HTTPException(status_code=401, detail="MT5 authorization failed. Check account number, password, and server.")
            elif "initialization failed" in error_msg.lower():
                raise HTTPException(status_code=503, detail="MT5 terminal is not available. Please ensure MetaTrader 5 is installed and running.")
            else:
                raise HTTPException(status_code=400, detail=f"MT5 connection failed: {error_msg}")

        existing_credentials = get_mt5_credentials(db, credentials.user_id)
        if existing_credentials:
            updated_credentials = update_mt5_credentials(db, credentials.user_id, {
                "account": str(credentials.account),
                "password": credentials.password,
                "server": credentials.server,
                "days": credentials.days
            })
            action = "updated"
        else:
            updated_credentials = create_mt5_credentials(db, {
                "account": str(credentials.account),
                "password": credentials.password,
                "server": credentials.server,
                "user_id": credentials.user_id,
                "days": credentials.days
            })
            action = "created"

        return {
            "status": "connected",
            "message": "Successfully connected to MT5",
            "trades_count": len(trades) if trades else 0,
            "account": credentials.account,
            "server": credentials.server,
            "action": action
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.delete("/disconnect-all", response_model=dict)
async def disconnect_mt5_full(user_id: str, db: Database = Depends(get_db)):
    """Fully disconnect: removes the EA token AND the stored MT5 credentials."""
    try:
        from app.services.analytics_service import clear_user_analytics_cache
        token_deleted = delete_mt5_connection(db, user_id)
        creds_deleted = delete_mt5_credentials(db, user_id)
        # Bust the analytics cache so the next request returns fresh (manual-only) stats
        clear_user_analytics_cache(user_id)
        if token_deleted or creds_deleted:
            return {"status": "disconnected", "message": "Successfully disconnected from MT5."}
        return {"status": "not_found", "message": "No active MT5 connection found."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/list-accounts", response_model=list)
async def list_mt5_accounts(user_id: str, db: Database = Depends(get_db)):
    """
    Return all MT5 accounts saved for this user.
    Each record has: account_id, server, label, is_active.
    """
    try:
        accounts = list(db.mt5_accounts.find({"user_id": user_id}))
        result = []
        for a in accounts:
            a.pop("_id", None)
            result.append({
                "account_id": a.get("account_id"),
                "server": a.get("server", ""),
                "label": a.get("label", f"Account #{a.get('account_id')}"),
                "is_active": a.get("is_active", False),
            })
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/switch-account", response_model=dict)
async def switch_mt5_account(user_id: str, account_id: str, db: Database = Depends(get_db)):
    """
    Switch the active MT5 account for this user.
    Deactivates all other accounts and activates the given one.
    """
    try:
        # Deactivate all
        db.mt5_accounts.update_many(
            {"user_id": user_id},
            {"$set": {"is_active": False}}
        )
        # Activate target
        result = db.mt5_accounts.update_one(
            {"user_id": user_id, "account_id": account_id},
            {"$set": {"is_active": True}}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail=f"Account {account_id} not found for this user.")
        # Also update legacy mt5_credentials to reflect the active account
        creds = db.mt5_accounts.find_one({"user_id": user_id, "account_id": account_id})
        if creds:
            db.mt5_credentials.update_one(
                {"user_id": user_id},
                {"$set": {"account": account_id, "server": creds.get("server", ""), "is_active": True}},
                upsert=True
            )
        return {"status": "switched", "active_account": account_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account-info", response_model=dict)
async def get_account_info(user_id: str, db: Database = Depends(get_db)):
    """Get MT5 account information."""
    try:
        credentials = get_mt5_credentials(db, user_id)
        if not credentials:
            raise HTTPException(status_code=404, detail="No MT5 credentials found")
        return {
            "account": credentials["account"],
            "server": credentials["server"],
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to get account info: {str(e)}")