import sys
import os

# Fix for Vercel read-only file system
if os.environ.get('VERCEL'):
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException, Request
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import RequestValidationError
from pymongo.database import Database
import pymongo
from typing import List, Optional
import logging
from datetime import datetime, timedelta

# Import database and CRUD
from app.mongo_database import db_client, get_db
from app.crud.user_crud import (
    create_user, get_user, get_user_by_id, get_user_by_email, get_user_by_account,
    update_password, create_password_reset_token, verify_password_reset_token,
    login_user
)
from app.crud.trade_crud import (
    create_trade, get_trades, get_trade_by_trade_no, get_trade_by_ticket,
    delete_trade, update_trade_reason, update_trade, update_trade_journal
)
from app.crud.mt5_crud import (
    create_mt5_credentials, get_mt5_credentials,
    update_mt5_credentials, delete_mt5_credentials
)

# Import services
from app.services.mt5_service import fetch_mt5_trades, calculate_profit_loss

# Import schemas
from app.schemas.user_schema import (
    UserCreate, UserBase, UserResponse,
    UserLogin, ForgotPasswordRequest, ResetPasswordRequest
)
from app.schemas.trade_schema import TradeBase
from app.schemas.mt5_schema import MT5CredentialsCreate, MT5CredentialsResponse

# Import route modules
from app.routes import (
    auth, admin, admin_users, admin_trades, admin_system, admin_analytics,
    announcements, analytics, subscription, reports, posts, notifications,
    mistakes, leaderboard, goals, chat, mt5, discipline, users, trades, friends, market_data, calendar, onboarding, backtest, tv_webhook
)

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="JournalX Trading Backend")

# ── Rate Limiting (slowapi) ────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

@app.get("/api/version")
async def get_version():
    return {
        "version": "v3.0-meeting-uuid-fix", 
        "timestamp": "2026-02-28 05:35:00"
    }

@app.get("/api/debug-market")
async def debug_market(symbol: str = "BTCUSDT"):
    import requests
    results = {}
    
    # 1. Test Standard Binance
    try:
        r = requests.get("https://api.binance.com/api/v3/klines", params={"symbol": symbol, "interval": "1h", "limit": 1}, timeout=5)
        results["binance_std"] = {"status": r.status_code, "text_preview": r.text[:200]}
    except Exception as e:
        results["binance_std"] = {"error": str(e)}

    # 2. Test GCP Binance
    try:
        r = requests.get("https://api-gcp.binance.com/api/v3/klines", params={"symbol": symbol, "interval": "1h", "limit": 1}, timeout=5)
        results["binance_gcp"] = {"status": r.status_code, "text_preview": r.text[:200]}
    except Exception as e:
        results["binance_gcp"] = {"error": str(e)}

    # 3. Test KuCoin
    try:
        ku_sym = "BTC-USDT"
        r = requests.get("https://api.kucoin.com/api/v1/market/candles", params={"symbol": ku_sym, "type": "1hour"}, timeout=5)
        results["kucoin"] = {"status": r.status_code, "text_preview": r.text[:200]}
    except Exception as e:
        results["kucoin"] = {"error": str(e)}

    return results

# version for verification
APP_VERSION = "v1.2.0-CONSOLIDATED-FIX"

# CORS Configuration
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://journalx-trading.vercel.app",
    "https://journalx.vercel.app",
    "https://journal-x-backend.vercel.app",
    "https://journalxbackend-production.up.railway.app",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # For debugging, narrow down in production if possible
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Logging Middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"
    method = request.method
    url = request.url
    
    logger.info(f"📨 {method} {url} | Client: {client_ip}")

    try:
        response = await call_next(request)
        logger.info(f"✅ {method} {url} -> {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"❌ {method} {url} failed: {str(e)}")
        raise

# Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"❌ Validation error for {request.method} {request.url}: {exc.errors()}")
    return JSONResponse(status_code=422, content={"detail": exc.errors()})

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled error: {exc}")
    return JSONResponse(status_code=500, content={"detail": "Internal Server Error"})

# Startup Events
@app.on_event("startup")
async def startup_event():
    logger.info(f"🚀 Starting JournalX Backend {APP_VERSION}...")
    try:
        db_client.connect()
        logger.info("✅ MongoDB connection established")

        # ── Ensure indexes for multi-user performance ──────────────────────────
        db = db_client.db
        # Unique token index — makes /ea/sync token lookup O(log n) at any scale
        db.mt5_connections.create_index("token", unique=True, sparse=True)
        # user_id index for fast per-user queries
        db.mt5_connections.create_index("user_id", unique=True)
        # Unique compound index: (user_id, mt5_ticket) — permanently blocks duplicate trade inserts
        db.trades.drop_index("user_id_1_mt5_ticket_1")  # drop old non-unique version if exists
        db.trades.create_index([("user_id", 1), ("mt5_ticket", 1)], unique=True, sparse=True, name="user_id_1_mt5_ticket_1")
        logger.info("✅ MongoDB indexes ensured for mt5_connections & trades")

        # Start economic calendar auto-update scheduler
        from app.services.economic_calendar_service import economic_calendar_service
        economic_calendar_service.start_scheduler(db_client.db)
        logger.info("✅ Economic calendar scheduler started")
        
    except Exception as e:
        logger.error(f"⚠️ Startup error: {str(e)}")

# ----------------- Base Routes -----------------
@app.get("/")
def root():
    return {"message": "JournalX Trading API", "version": APP_VERSION}

@app.get("/health")
def health_check():
    db_status = "connected" if db_client.db is not None else "disconnected"
    return {
        "status": "healthy" if db_client.db is not None else "degraded",
        "version": APP_VERSION,
        "database": db_status,
        "timestamp": datetime.now().isoformat()
    }

# ----------------- Router Registration -----------------
# Order matters if there are overlapping prefixes
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(subscription.router, prefix="/api/subscriptions", tags=["Subscriptions"])
app.include_router(users.router, prefix="/api/users", tags=["Users"])
app.include_router(trades.router, prefix="/trades", tags=["Trades"])
app.include_router(mt5.router, prefix="/mt5", tags=["MT5"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])
app.include_router(admin_users.router, prefix="/api/admin/users", tags=["Admin Users"])
app.include_router(admin_trades.router, prefix="/api/admin/trades", tags=["Admin Trades"])
app.include_router(admin_system.router, prefix="/api/admin/system", tags=["Admin System"])
app.include_router(admin_analytics.router, prefix="/api/admin/analytics", tags=["Admin Analytics"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(announcements.router, prefix="/api/announcements", tags=["Announcements"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["Notifications"])
app.include_router(leaderboard.router, prefix="/api/leaderboard", tags=["Leaderboard"])
app.include_router(goals.router, prefix="/api/goals", tags=["Goals"])
app.include_router(discipline.router, prefix="/api/discipline", tags=["Discipline"])
app.include_router(reports.router, prefix="/api/reports", tags=["Reports"])
app.include_router(posts.router, prefix="/api/posts", tags=["Posts"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI Chat"])
app.include_router(mistakes.router, prefix="/api/mistakes", tags=["Mistakes"])
app.include_router(friends.router, prefix="/api/friends", tags=["Friends"])
app.include_router(market_data.router, prefix="/api/market-data", tags=["Market Data"])
app.include_router(calendar.router, prefix="/api/calendar", tags=["Economic Calendar"])
app.include_router(onboarding.router, prefix="/api/onboarding", tags=["Onboarding"])
app.include_router(backtest.router, prefix="/api/backtest", tags=["Backtesting"])
app.include_router(tv_webhook.router, prefix="/api/integrations/tradingview", tags=["TradingView Integration"])

# ----------------- Direct Routes (Legacy/Core) -----------------

@app.post("/register", response_model=UserResponse)
def register_user_endpoint(user: UserCreate, db: Database = Depends(get_db)):
    db_user = get_user_by_email(db, user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    user_data = user.model_dump()
    user_data.pop("confirm_password", None)
    return create_user(db, user_data)

@app.post("/forgot-password")
def forgot_password_endpoint(request: ForgotPasswordRequest, db: Database = Depends(get_db)):
    user = get_user_by_email(db, request.email)
    if not user:
        return {"message": "If the email exists, a reset link will be sent"}
    token = create_password_reset_token(request.email)
    return {"message": "Token generated", "reset_token": token, "email": request.email}

@app.post("/reset-password")
def reset_password_endpoint(request: ResetPasswordRequest, db: Database = Depends(get_db)):
    email = verify_password_reset_token(request.token)
    if not email or not get_user_by_email(db, email):
        raise HTTPException(status_code=400, detail="Invalid token")
    update_password(db, email, request.new_password)
    return {"message": "Password reset successfully"}

@app.get("/trades/user/{user_id}", response_model=List[TradeBase])
def get_user_trades(user_id: str, skip: int = 0, limit: int = 1000, sort: str = "desc", db: Database = Depends(get_db)):
    """
    Get paginated trades for a user.
    """
    import logging
    logging.info(f"\n\n🚨 [DEBUG] BROWSER REQUESTED GET TRADES FOR: {user_id}\n\n")
    user = get_user_by_id(db, user_id)
    sub_tier = user.get("subscription_tier", "free") if user else "free"
    sort_desc = (sort.lower() == "desc")
    sort_dir = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING

    # Active account isolation — allow str AND int variants so type differences don't break it
    mt5_creds = get_mt5_credentials(db, user_id)
    raw_account = mt5_creds.get("account") if mt5_creds else None
    active_account = str(raw_account) if raw_account is not None else None

    query = {"user_id": user_id}
    if active_account:
        # Connected: show ONLY this account's trades (strict isolation)
        query["$or"] = [
            {"mt5_account": active_account},
            {"mt5_account": raw_account},       # int variant type-safety
        ]
    else:
        # Disconnected: return nothing at all
        query["mt5_account"] = "__NO_ACCOUNT_CONNECTED__"

    if sub_tier == "free":
        limit_date = datetime.now() - timedelta(days=30)
        date_cond = {"$or": [
            {"close_time": {"$gte": limit_date}},
            {"close_time": None, "open_time": {"$gte": limit_date}}
        ]}
        # Combine with account filter using $and
        if "$or" in query:
            account_cond = {"$or": query.pop("$or")}
            query["$and"] = [account_cond, date_cond]
        else:
            query.update(date_cond)
        return list(db.trades.find(query).sort("trade_no", sort_dir).skip(skip).limit(limit))

    return get_trades(db, user_id, skip, limit, sort_desc, active_account=active_account)

@app.post("/users/{user_id}/fetch-mt5-trades")
def fetch_user_mt5_trades(user_id: str, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    credentials = get_mt5_credentials(db, user_id)
    if not credentials:
        raise HTTPException(status_code=404, detail="MT5 credentials not found")
    
    sub_tier = user.get("subscription_tier", "free")
    fetch_days = 3650  # Unlimited pull for all trades (10 years)
    
    try:
        trades = fetch_mt5_trades(
            int(credentials["account"]), credentials["password"], credentials["server"], fetch_days
        )
        saved, updated, skipped = 0, 0, 0
        account_str = str(credentials["account"])

        for t in (trades or []):
            ticket = t.get("ticket")
            if not ticket:
                skipped += 1
                continue

            p, l = calculate_profit_loss(t.get("profit", 0.0))
            trade_data = {
                "user_id": user_id,
                "mt5_ticket": ticket,
                "symbol": t.get("symbol"),
                "volume": t.get("volume"),
                "price_open": t.get("price_open"),
                "price_close": t.get("price_close"),
                "type": t.get("type"),
                "net_profit": t.get("profit"),
                "profit_amount": p,
                "loss_amount": l,
                "reason": "MT5 Fetch",
                "open_time": t.get("time"),
                "close_time": t.get("time"),
                "mt5_account": account_str
            }

            # ── Step 1: Check by mt5_ticket (fast path) ─────────────────────
            existing = db.trades.find_one({"user_id": user_id, "mt5_ticket": ticket})

            # ── Step 2: Fingerprint fallback for legacy rows without mt5_ticket
            if not existing:
                open_str = str(t.get("time", ""))[:16]  # minute-level match
                existing = db.trades.find_one({
                    "user_id": user_id,
                    "mt5_account": account_str,
                    "mt5_ticket": {"$in": [None, ""]},   # only look at untagged rows
                    "symbol": t.get("symbol"),
                    "type": t.get("type"),
                    "volume": t.get("volume"),
                    "net_profit": t.get("profit"),
                })

            if existing:
                # Stamp the ticket and refresh close-side fields
                db.trades.update_one(
                    {"_id": existing["_id"]},
                    {"$set": {
                        "mt5_ticket": ticket,
                        "price_close": t.get("price_close"),
                        "net_profit": t.get("profit"),
                        "profit_amount": p,
                        "loss_amount": l,
                        "mt5_account": account_str
                    }}
                )
                updated += 1
            else:
                create_trade(db, trade_data)
                saved += 1

        return {"total": len(trades or []), "saved": saved, "updated": updated, "skipped": skipped}
    except Exception as e:
        logger.error(f"MT5 Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/routes")
def list_all_routes():
    return [{"path": r.path, "methods": list(r.methods) if hasattr(r, 'methods') else [], "name": getattr(r, 'name', '')} for r in app.routes]
