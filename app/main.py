import sys
import os

# Fix for Vercel read-only file system
if os.environ.get('VERCEL'):
    os.environ['MPLCONFIGDIR'] = '/tmp/matplotlib'

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, Depends, HTTPException, Request
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
    mistakes, leaderboard, goals, chat, mt5, discipline, users, trades, friends, market_data
)

# Initialize Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="JournalX Trading Backend")

@app.get("/api/version")
async def get_version():
    return {"version": "v2.1-httpx-fix", "timestamp": "2026-02-09 02:10:00"}

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
    except Exception as e:
        logger.error(f"⚠️ Database connection failed: {str(e)}")

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
    user = get_user_by_id(db, user_id)
    sub_tier = user.get("subscription_tier", "free") if user else "free"
    sort_desc = (sort.lower() == "desc")
    
    if sub_tier == "free":
        limit_date = datetime.now() - timedelta(days=30)
        sort_dir = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING
        query = {
            "user_id": user_id,
            "$or": [
                {"close_time": {"$gte": limit_date}},
                {"close_time": None, "open_time": {"$gte": limit_date}}
            ]
        }
        return list(db.trades.find(query).sort("trade_no", sort_dir).skip(skip).limit(limit))
    
    return get_trades(db, user_id, skip, limit, sort_desc)

@app.post("/users/{user_id}/fetch-mt5-trades")
def fetch_user_mt5_trades(user_id: str, db: Database = Depends(get_db)):
    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    credentials = get_mt5_credentials(db, user_id)
    if not credentials:
        raise HTTPException(status_code=404, detail="MT5 credentials not found")
    
    sub_tier = user.get("subscription_tier", "free")
    fetch_days = 90 if sub_tier != "free" else 30
    
    try:
        trades = fetch_mt5_trades(
            int(credentials["account"]), credentials["password"], credentials["server"], fetch_days
        )
        saved, skipped = 0, 0
        for t in (trades or []):
            if get_trade_by_ticket(db, t['ticket']):
                skipped += 1
                continue
            
            p, l = calculate_profit_loss(t.get('profit', 0.0))
            create_trade(db, {
                "user_id": user_id, "symbol": t.get('symbol'), "volume": t.get('volume'),
                "price_open": t.get('price_open'), "price_close": t.get('price_close'),
                "type": t.get('type'), "net_profit": t.get('profit'),
                "profit_amount": p, "loss_amount": l, "reason": "MT5 Fetch",
                "open_time": t.get('time'), "close_time": t.get('time')
            })
            saved += 1
        return {"total": len(trades or []), "saved": saved, "skipped": skipped}
    except Exception as e:
        logger.error(f"MT5 Fetch error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/debug/routes")
def list_all_routes():
    return [{"path": r.path, "methods": list(r.methods) if hasattr(r, 'methods') else [], "name": getattr(r, 'name', '')} for r in app.routes]
