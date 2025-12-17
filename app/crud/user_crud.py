from pymongo.database import Database
import secrets
import datetime
import hashlib
import logging
import uuid

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# ------------------- Password Helpers -------------------
def get_password_hash(password: str) -> str:
    """Hash the password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain password against hashed password"""
    return get_password_hash(plain_password) == hashed_password

# ------------------- User Queries -------------------
def get_user(db: Database, user_id: str):
    return db.users.find_one({"user_id": user_id})

def get_user_by_id(db: Database, user_id: str):
    return db.users.find_one({"user_id": user_id})

def get_user_by_email(db: Database, email: str):
    return db.users.find_one({"email": email})

def get_user_by_account(db: Database, account_number: int):
    # Find credentials first
    credentials = db.mt5_credentials.find_one({"account": str(account_number)})
    if credentials:
        return db.users.find_one({"user_id": credentials["user_id"]})
    return None

def get_all_users(db: Database, skip: int = 0, limit: int = 100):
    users = list(db.users.find().skip(skip).limit(limit))
    return users

# ------------------- User Creation -------------------
def create_user(db: Database, user_data: dict):
    """Create a new user with permanent UUID"""
    user_id = str(uuid.uuid4())
    
    new_user = {
        "user_id": user_id,
        "first_name": user_data['first_name'],
        "last_name": user_data['last_name'],
        "email": user_data['email'],
        "password": get_password_hash(user_data['password']),
        "mobile_number": user_data.get('mobile_number', ''),
        "role": "user",
        "is_active": True,
        "created_at": datetime.datetime.now()
    }
    
    db.users.insert_one(new_user)
    print(f"✅ Created user {new_user['email']} with permanent ID: {user_id}")
    return new_user

# ------------------- Authentication -------------------
def login_user(db: Database, email: str, password: str):
    """Authenticate user with email and password"""
    user = get_user_by_email(db, email)
    if user and verify_password(password, user["password"]):
        print(f"📊 Logged in user: {user['email']} with ID: {user['user_id']}")
        return user
    return None

def update_password(db: Database, email: str, new_password: str):
    hashed_pw = get_password_hash(new_password)
    result = db.users.update_one(
        {"email": email},
        {"$set": {"password": hashed_pw}}
    )
    if result.modified_count > 0:
        return get_user_by_email(db, email)
    return None

def update_user_profile(db: Database, user_id: str, update_data: dict):
    """Update user profile fields"""
    # Filter out None values to avoid overwriting with null
    fields_to_update = {k: v for k, v in update_data.items() if v is not None}
    
    if not fields_to_update:
        return get_user_by_id(db, user_id)
        
    result = db.users.update_one(
        {"user_id": user_id},
        {"$set": fields_to_update}
    )
    
    if result.acknowledged:
        return get_user_by_id(db, user_id)
    return None

def change_password(db: Database, user_id: str, current_password: str, new_password: str) -> bool:
    """Change user password after verifying current password"""
    user = get_user_by_id(db, user_id)
    if not user:
        return False
    
    # Verify current password
    if not verify_password(current_password, user["password"]):
        return False
    
    # Update with new password
    hashed_pw = get_password_hash(new_password)
    result = db.users.update_one(
        {"user_id": user_id},
        {"$set": {"password": hashed_pw}}
    )
    
    return result.modified_count > 0

# ------------------- Password Reset -------------------
password_reset_tokens = {}

def create_password_reset_token(email: str):
    """Generate a token for password reset valid for 1 hour"""
    token = secrets.token_urlsafe(32)
    expires = datetime.datetime.now() + datetime.timedelta(hours=1)
    password_reset_tokens[token] = {
        "email": email,
        "expires": expires
    }
    # Always print token for debugging/fallback
    print(f"🎯 PASSWORD RESET TOKEN for {email}: {token}")
    print(f"🌐 Reset URL: http://localhost:3000/reset-password?token={token}")
    
    # Send email fallback logic preserved
    _send_password_reset_email(email, token)
        
    return token

def _send_password_reset_email(email: str, token: str) -> bool:
    """Send email via service if configured; return True if successful"""
    try:
        from app.services.email_service import email_service
        if not hasattr(email_service, 'sendgrid_api_key') or not email_service.sendgrid_api_key:
            return False
        success = email_service.send_password_reset_email(email, token)
        return success
    except (ImportError, Exception):
        return False

def verify_password_reset_token(token: str):
    """Verify reset token validity"""
    if token not in password_reset_tokens:
        return None
    token_data = password_reset_tokens[token]
    if datetime.datetime.now() > token_data["expires"]:
        del password_reset_tokens[token]
        return None
    return token_data["email"]
