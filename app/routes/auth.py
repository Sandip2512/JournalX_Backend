from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pymongo.database import Database
from datetime import datetime, timedelta, timezone
import os
import logging
from dotenv import load_dotenv

from app.mongo_database import get_db
from app.crud.user_crud import login_user
from app.schemas.user_schema import UserLogin, UserResponse, UserUpdate

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

load_dotenv()
# Support both SECRET_KEY (local) and JWT_SECRET (Vercel configuration)
SECRET_KEY = os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "fallback_secret"
# Support both ALGORITHM (local) and JWT_ALGORITHM (Vercel configuration)
ALGORITHM = os.getenv("ALGORITHM") or os.getenv("JWT_ALGORITHM") or "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", 1440))

router = APIRouter()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

def get_current_user(token: str = Depends(oauth2_scheme), db: Database = Depends(get_db)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            logger.warning("🚫 Token missing 'sub' claim")
            raise HTTPException(status_code=401, detail="Invalid token")
            
        # Use a timeout to avoid hangs
        user = db.users.find_one({"email": email}, max_time_ms=2000)
        if user is None:
             logger.warning(f"🚫 User not found for email: {email}")
             raise HTTPException(status_code=401, detail="User not found")
        
        # Auto-fix/fallback for legacy users missing permanent user_id
        if "user_id" not in user:
            logger.info(f"🔧 Missing user_id for {email}, falling back to MongoDB _id")
            user["user_id"] = str(user["_id"])
             
        # Update last_seen activity (non-critical, wrap in try-except)
        try:
            db.users.update_one(
                {"user_id": user["user_id"]},
                {"$set": {"last_seen": datetime.utcnow()}}
            )
        except Exception as e:
            logger.error(f"⚠️ Failed to update last_seen for {email}: {e}")
             
        return user
    except JWTError:
        logger.warning("🚫 JWT validation failed")
        raise HTTPException(status_code=401, detail="Could not validate credentials")
    except Exception as e:
        logger.error(f"❌ Error in get_current_user: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal auth error")

# Alias for compatibility with some routes
get_current_user_role = get_current_user

def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

@router.post("/login")
def login(user_login: UserLogin, request: Request, background_tasks: BackgroundTasks, db: Database = Depends(get_db)):
    client_ip = request.client.host
    
    try:
        print(f"🔐 Login attempt for email: {user_login.email}")
        
        # login_user returns a dict or None (since migrated)
        db_user = login_user(db, user_login.email, user_login.password)
        
        if not db_user:
            print("❌ Login failed: Invalid credentials or user not found")
            raise HTTPException(status_code=401, detail="Invalid credentials")

        # Auto-fix/fallback for legacy users missing permanent user_id
        if "user_id" not in db_user:
            logger.info(f"🔧 Standardizing missing user_id for {user_login.email} during login")
            db_user["user_id"] = str(db_user["_id"])

        # Record success in background
        background_tasks.add_task(log_login_history, db_user["user_id"], client_ip, "success", db)

        print(f"✅ Login successful!")
        
        access_token = create_access_token(
            data={
                "sub": db_user["email"], 
                "user_id": db_user["user_id"],
                "role": db_user.get("role", "user") 
            },
            expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        )

        # Ensure _id is handled if present (Pydantic can ignore it if extra="ignore", but safer to use schema safely)
        # UserResponse expects fields. db_user is a dict.
        user_data = UserResponse(**db_user)

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": user_data
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        # import traceback
        # traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

def log_login_history(user_id: str, ip_address: str, status: str, db: Database):
    try:
        # We can use the passed 'db' object because in PyMongo it's thread-safe / pool-based usually.
        # However, BackgroundTasks might run after request context is gone. 
        # But 'db' from dependency is usually a client.get_database(), which is persistent in pymongo client.
        # But let's be safe and grab a fresh reference if needed, but for pymongo passing it is usually fine 
        # unlike SQLAlchemy session which is scoped.
        # Actually, `get_db` yields `db_client.db`. It's a single object for the app lifespan (singleton style in mongo_database.py). 
        # So it is safe to reuse.
        
        log = {
            "user_id": user_id,
            "ip_address": ip_address,
            "status": status,
            "timestamp": datetime.now(timezone.utc)
        }
        db.login_history.insert_one(log)
    except Exception as e:
        print(f"⚠️ Failed to log login history: {e}")

@router.put("/profile", response_model=UserResponse)
def update_profile(
    user_update: UserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    db: Database = Depends(get_db)
):
    """
    Update current user's profile and settings.
    Clients can update first_name, last_name, mobile, daily_loss_limit, max_daily_trades.
    """
    update_data = user_update.model_dump(exclude_unset=True)
    
    if not update_data:
        return current_user
        
    db.users.update_one(
        {"user_id": current_user["user_id"]},
        {"$set": update_data}
    )
    
    updated_user = db.users.find_one({"user_id": current_user["user_id"]})
    return UserResponse(**updated_user)
