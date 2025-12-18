from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pymongo.database import Database
from typing import List
import logging
from datetime import datetime

from app.mongo_database import db_client, get_db
# Note: CRUD imports will be broken until refactored
from app.crud.trade_crud import create_trade, get_trades, get_trade_by_trade_no, delete_trade, update_trade_reason
from app.crud.user_crud import (
    create_user, get_user, get_user_by_id, get_user_by_email, get_user_by_account,
    update_password, create_password_reset_token, verify_password_reset_token,
    login_user
)
from app.crud.mt5_crud import create_mt5_credentials, get_mt5_credentials, update_mt5_credentials, delete_mt5_credentials
from app.services.mt5_service import fetch_mt5_trades, calculate_profit_loss
from app.schemas.trade_schema import TradeCreate, TradeBase
from app.schemas.user_schema import (
    UserCreate, UserBase, UserResponse,
    UserLogin, ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.mt5_schema import MT5CredentialsCreate, MT5CredentialsResponse

# Import routers
from app.routes.auth import router as auth_router
from app.routes import mt5, leaderboard, goals  # Import mt5, leaderboard, goals routers

# Logging - MUST be initialized before middleware
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Forex Trading Journal Backend")

# ----------------- CORS SETUP -----------------
# Include all possible origins including network IP if used
# Include specific origins for localhost
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:4200",
    "http://127.0.0.1:4200",
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://192.168.1.3:8080",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)



# Exception handlers
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    import traceback
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)}
    )

# Startup event to verify server initialization
@app.on_event("startup")
async def startup_event():
    logger.info("🚀 Starting FastAPI server...")
    logger.info("📡 Server will be available at http://127.0.0.1:8000")
    logger.info(f"🌐 CORS enabled for: {', '.join(origins)}")
    try:
        # Connect to MongoDB
        db_client.connect()
        logger.info("✅ MongoDB connection established")
        logger.info("✅ Server startup complete!")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {str(e)}")
        raise



# ----------------- ROOT -----------------
@app.get("/")
def root():
    return {"message": "Trading History App is running 🚀"}

# ----------------- Health Check -----------------
@app.get("/health")
def health_check():
    """Health check endpoint to verify server is running and database connectivity"""
    try:
        # Check database connectivity properly without boolean evaluation
        db_status = "connected" if db_client.db is not None else "disconnected"
        
        # Try to ping the database if connected
        if db_client.db is not None:
            try:
                db_client.client.admin.command('ping')
                db_healthy = True
            except Exception:
                db_healthy = False
                db_status = "error"
        else:
            db_healthy = False
        
        return {
            "status": "healthy" if db_healthy else "degraded",
            "message": "Backend server is running",
            "database": db_status,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {
            "status": "degraded",
            "message": "Backend server is running but database check failed",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

@app.get("/test")
def test_connection():
    """Simple test endpoint to verify backend connection"""
    return {
        "success": True,
        "message": "Backend is connected and responding",
        "server": "FastAPI",
        "timestamp": datetime.now().isoformat()
    }

# ----------------- MT5 Connection Status -----------------
@app.get("/users/{user_id}/mt5-status")
def get_mt5_connection_status(user_id: str, db: Database = Depends(get_db)):
    """Check MT5 connection status and last fetch time"""
    try:
        # Get user
        user = get_user_by_id(db, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Get MT5 credentials
        credentials = get_mt5_credentials(db, user_id)
        if not credentials:
            return {
                "connected": False,
                "has_credentials": False,
                "message": "No MT5 credentials found. Please connect your MT5 account first.",
                "last_fetch": None
            }
        
        # Get most recent trade to determine last fetch time
        recent_trades = get_trades(db, user_id, 0, 1)
        last_fetch = None
        if recent_trades and len(recent_trades) > 0:
            # We already fetched it sorted in get_trades? 
            # get_trades in crud uses .sort("close_time", -1). 
            # So the first one is recent.
            # But the logic below tries to sort by open_time.
            # Let's trust get_trades or query directly.
            most_recent = db.trades.find_one(
                {"user_id": user_id},
                sort=[("open_time", -1)]
            )
            
            if most_recent:
                ot = most_recent.get("open_time")
                last_fetch = ot.isoformat() if hasattr(ot, 'isoformat') else str(ot)
        
        return {
            "connected": True,
            "has_credentials": True,
            "account": credentials.get("account"),
            "server": credentials.get("server"),
            "last_fetch": last_fetch,
            "message": "MT5 credentials configured. Ready to fetch trades."
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking MT5 status: {str(e)}")
        return {
            "connected": False,
            "has_credentials": False,
            "message": f"Error checking status: {str(e)}",
            "last_fetch": None
        }

# ----------------- Debug Endpoints -----------------
@app.get("/debug/user/{user_id}")
def debug_user(user_id: str, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if user:
        return {
            "exists": True, 
            "user": {
                "user_id": user.get("user_id"),
                "email": user.get("email"),
                "first_name": user.get("first_name"),
                "last_name": user.get("last_name"),
                "created_at": user.get("created_at")
            }
        }
    else:
        return {"exists": False, "message": f"User {user_id} not found"}

@app.get("/debug/mt5-credentials/{user_id}")
def debug_mt5_credentials(user_id: str, db: Database = Depends(get_db)):
    credentials = get_mt5_credentials(db, user_id)
    if credentials:
        return {
            "exists": True, 
            "credentials": {
                "account": credentials.get("account"),
                "server": credentials.get("server"),
                "user_id": credentials.get("user_id"),
                "has_password": bool(credentials.get("password"))
            }
        }
    else:
        return {"exists": False, "message": "No MT5 credentials found"}

# ----------------- Auth Routes -----------------
app.include_router(auth_router, prefix="/api/auth", tags=["Auth"])

# ----------------- MT5 Routes -----------------
from app.routes import auth, admin, admin_users, admin_trades, admin_system, admin_analytics, announcements, analytics, subscription, reports

app.include_router(mt5.router, prefix="/mt5", tags=["MT5"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["Admin Users"])
app.include_router(admin_trades.router, prefix="/api/admin/trades", tags=["admin-trades"])
app.include_router(admin_system.router, prefix="/api/admin/system", tags=["Admin System"])
app.include_router(admin_analytics.router, prefix="/api/admin/analytics", tags=["Admin Analytics"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["announcements"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["Leaderboard"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(subscription.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
from app.routes import users
app.include_router(users.router, prefix="/api/users", tags=["Users"])

# ----------------- User Endpoints -----------------
@app.post("/register", response_model=UserResponse)
def register_user(user: UserCreate, db: Database = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_data = user.model_dump()
    user_data.pop("confirm_password", None)
    new_user = create_user(db, user_data)
    # new_user is a dict including _id, Pydantic should ignore extra if config allows, or we pass dict directly
    # UserResponse(**new_user)
    return new_user

@app.post("/forgot-password")
def forgot_password(request: ForgotPasswordRequest, db: Database = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user:
        return {"message": "If the email exists, a password reset link has been sent"}
    
    reset_token = create_password_reset_token(request.email)
    return {
        "message": "Password reset token generated",
        "reset_token": reset_token,
        "email": request.email
    }

@app.post("/reset-password")
def reset_password(request: ResetPasswordRequest, db: Database = Depends(get_db)):
    email = verify_password_reset_token(request.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired token")
    
    user = get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_password(db, email, request.new_password)
    return {"message": "Password reset successfully"}

@app.get("/users/profile/{user_id}", response_model=UserResponse)
def get_user_profile(user_id: str, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

# ----------------- MT5 Credentials Endpoints -----------------
@app.post("/users/{user_id}/mt5-credentials", response_model=MT5CredentialsResponse)
def add_mt5_credentials(user_id: str, credentials: MT5CredentialsCreate, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    creds_data = credentials.model_dump()
    creds_data["account"] = str(creds_data["account"])
    creds_data["user_id"] = user_id
    
    try:
        if get_mt5_credentials(db, user_id):
             raise HTTPException(
                status_code=400,
                detail="You already have this MT5 account registered. Use update instead."
            )
        return create_mt5_credentials(db, creds_data)
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error creating credentials: {str(e)}"
        )

@app.get("/users/{user_id}/mt5-credentials", response_model=MT5CredentialsResponse)
def get_user_mt5_credentials(user_id: str, db: Database = Depends(get_db)):
    credentials = get_mt5_credentials(db, user_id)
    if not credentials:
        raise HTTPException(status_code=404, detail="No MT5 credentials found for this user")
    return credentials

@app.put("/users/{user_id}/mt5-credentials", response_model=MT5CredentialsResponse)
def update_user_mt5_credentials(user_id: str, credentials: MT5CredentialsCreate, db: Database = Depends(get_db)):
    update_data = credentials.model_dump()
    update_data["account"] = str(update_data["account"])
    
    updated = update_mt5_credentials(db, user_id, update_data)
    if not updated:
        raise HTTPException(status_code=404, detail="No MT5 credentials found for this user")
    return updated

@app.delete("/users/{user_id}/mt5-credentials")
def delete_user_mt5_credentials(user_id: str, db: Database = Depends(get_db)):
    deleted = delete_mt5_credentials(db, user_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="No MT5 credentials found for this user")
    return {"message": "MT5 credentials deleted successfully"}

# ----------------- Trade Endpoints -----------------
@app.get("/trades", response_model=List[TradeBase])
def get_all_trades(skip: int = 0, limit: int = 100, db: Database = Depends(get_db)):
    trades = list(db.trades.find().skip(skip).limit(limit))
    return trades

@app.get("/trades/user/{user_id}", response_model=List[TradeBase])
def get_trades_by_user(user_id: str, skip: int = 0, limit: int = 100, db: Database = Depends(get_db)):
    trades = get_trades(db, user_id, skip, limit)
    if not trades:
        return []  # Return empty array instead of 404
    return trades

@app.get("/trades/trade/{trade_no}", response_model=TradeBase)
def get_trade_by_number(trade_no: int, db: Database = Depends(get_db)):
    trade = get_trade_by_trade_no(db, trade_no)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return trade

@app.put("/trades/{trade_no}")
def update_trade_reason_mistake(trade_no: int, reason: str, mistake: str, db: Database = Depends(get_db)):
    trade = update_trade_reason(db, trade_no, reason, mistake)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    return {"message": "Trade updated successfully"}

@app.delete("/trades/trade/{trade_no}")
def delete_trade_by_number(trade_no: int, db: Database = Depends(get_db)):
    trade = get_trade_by_trade_no(db, trade_no)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    delete_trade(db, trade_no)
    return {"message": f"Trade {trade_no} deleted successfully"}

@app.post("/trades", response_model=TradeBase)
def create_trade_endpoint(trade: TradeCreate, db: Database = Depends(get_db)):
    """Create a new trade manually"""
    try:
        # trade_no will be auto-generated in create_trade if not provided
        # Create the trade
        trade_data = trade.model_dump()
        new_trade = create_trade(db, trade_data)
        return new_trade
    # except IntegrityError as e: # IntegrityError is SQLAlchemy
    #     db.rollback()
    #     logger.error(f"Integrity error creating trade: {str(e)}")
    #     raise HTTPException(status_code=400, detail="Error creating trade. Trade number may already exist.")
    except HTTPException:
        raise
    except Exception as e:
        # db.rollback() # No rollback in mongo single ops
        logger.error(f"Error creating trade: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error creating trade: {str(e)}")

# ----------------- Fetch MT5 Trades -----------------
# ----------------- Fetch MT5 Trades -----------------
@app.post("/users/{user_id}/fetch-mt5-trades")
def fetch_mt5_trades_endpoint(user_id: str, db: Database = Depends(get_db)):
    try:
        print(f"🔍 Fetch MT5 trades called for user: {user_id}")
        
        # Try to get user by UUID first
        user = get_user_by_id(db, user_id)
        
        # If not found, try to get user by MT5 account number (in case frontend sends account number)
        if not user:
            try:
                account_number = int(user_id)
                user = get_user_by_account(db, account_number)
                if user:
                    print(f"✅ Found user by account number: {account_number} -> {user.get('user_id')}")
                    user_id = user.get("user_id")  # Update user_id to the actual UUID
            except ValueError:
                pass  # user_id is not a number, continue with original user_id
        
        if not user:
            print("❌ User not found in database")
            raise HTTPException(status_code=404, detail="User not found")
        
        credentials = get_mt5_credentials(db, user_id)
        if not credentials:
            print("❌ No MT5 credentials found for user")
            raise HTTPException(status_code=404, detail="No MT5 credentials found")
        
        # Validate credentials
        if not credentials.get("account"):
            raise HTTPException(status_code=400, detail="MT5 account number is missing")
        if not credentials.get("password"):
            raise HTTPException(status_code=400, detail="MT5 password is missing")
        if not credentials.get("server"):
            raise HTTPException(status_code=400, detail="MT5 server is missing")
        
        # Convert account to int safely
        try:
            account_number = int(credentials.get("account"))
        except (ValueError, TypeError) as e:
            raise HTTPException(status_code=400, detail=f"Invalid MT5 account number: {credentials.get('account')}")
        
        # Fetch trades from MT5
        try:
            trades = fetch_mt5_trades(
                account=account_number,
                password=credentials.get("password"),
                server=credentials.get("server"),
                days=90
            )
        except Exception as mt5_error:
            error_msg = str(mt5_error)
            print(f"❌ MT5 fetch error: {error_msg}")
            # Check for specific MT5 errors
            if "disconnected" in error_msg.lower() or "connection lost" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail="MT5 account disconnected from broker server. Please ensure MT5 terminal is connected to the broker server (check the connection status in MT5). Wait a few seconds for the connection to stabilize, then try again."
                )
            elif "IPC timeout" in error_msg or "(-10005" in error_msg:
                raise HTTPException(
                    status_code=503,
                    detail="MT5 terminal is not responding (IPC timeout). This may occur if the account disconnected from the server. Please check MT5 connection status, wait for it to reconnect, then try again."
                )
            elif "Authorization failed" in error_msg or "(-6" in error_msg:
                raise HTTPException(
                    status_code=401,
                    detail="MT5 authorization failed. Please reconnect with correct credentials."
                )
            elif "initialization failed" in error_msg.lower():
                raise HTTPException(
                    status_code=503,
                    detail="MT5 terminal is not available. Please ensure MetaTrader 5 is installed and running."
                )
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to fetch trades from MT5: {error_msg}"
                )
        
        # Ensure trades is a list
        if trades is None:
            trades = []
        
        saved_count, skipped_count, error_count = 0, 0, 0
        
        # Process each trade
        for trade_data in trades:
            try:
                # Validate required fields
                if 'ticket' not in trade_data:
                    error_count += 1
                    logger.warning(f"Skipping trade with missing ticket: {trade_data}")
                    continue
                
                existing_trade = get_trade_by_ticket(db, trade_data['ticket'])
                if existing_trade:
                    skipped_count += 1
                    continue
                
                profit_amt, loss_amt = calculate_profit_loss(trade_data.get('profit', 0.0))
                
                trade_create = TradeCreate(
                    user_id=user_id,
                    symbol=trade_data.get('symbol', 'UNKNOWN'),
                    volume=trade_data.get('volume', 0.0),
                    price_open=trade_data.get('price_open', 0.0),
                    price_close=trade_data.get('price_close', 0.0),
                    type=trade_data.get('type', 'unknown'),
                    take_profit=trade_data.get('tp', 0.0),
                    stop_loss=trade_data.get('sl', 0.0),
                    profit_amount=profit_amt,
                    loss_amount=loss_amt,
                    net_profit=trade_data.get('profit', 0.0),
                    reason="Fetched from MT5",
                    mistake="To be analyzed",
                    open_time=trade_data.get('time', datetime.now()),
                    close_time=trade_data.get('time', datetime.now())
                )
                
                create_trade(db, trade_create.model_dump())
                saved_count += 1
            except Exception as e:
                error_count += 1
                logger.error(f"Error processing trade {trade_data.get('ticket', 'unknown')}: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
        
        return {
            "message": f"Trade fetch completed",
            "total_fetched": len(trades),
            "newly_saved": saved_count,
            "already_exist": skipped_count,
            "errors": error_count,
            "user_id": user_id
        }
    except HTTPException:
        # Re-raise HTTPExceptions as-is
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Unexpected error in fetch_mt5_trades_endpoint: {error_msg}")
        import traceback
        traceback.print_exc()
        logger.error(f"Unexpected error: {error_msg}")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred while fetching trades: {error_msg}"
        )

# ----------------- Trade Statistics -----------------
@app.get("/trades/stats/user/{user_id}")
def get_trade_statistics(user_id: str, db: Database = Depends(get_db)):
    trades = get_trades(db, user_id, 0, 1000)
    if not trades:
        return {"message": "No trades found", "user_id": user_id}
    
    total_trades = len(trades)
    # trades returned are dicts or Pydantic models? get_trades returns dicts now.
    # So we use key access.
    
    total_profit = sum((trade.get("profit_amount") or 0) for trade in trades)
    total_loss = sum((trade.get("loss_amount") or 0) for trade in trades)
    net_profit = total_profit - total_loss
    winning_trades = sum(1 for trade in trades if (trade.get("net_profit") or 0) > 0)
    losing_trades = total_trades - winning_trades
    
    return {
        "user_id": user_id,
        "total_trades": total_trades,
        "total_profit": total_profit,
        "total_loss": total_loss,
        "net_profit": net_profit,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate": (winning_trades / total_trades * 100) if total_trades > 0 else 0
    }

# ----------------- Debug All Endpoints -----------------
@app.get("/debug/all-endpoints")
async def debug_all_endpoints():
    all_routes = []
    for route in app.routes:
        if hasattr(route, 'methods'):
            all_routes.append({
                "path": route.path,
                "methods": list(route.methods),
                "name": getattr(route, "name", "unknown")
            })
    return all_routes
