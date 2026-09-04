import secrets
from datetime import datetime, timezone
from pymongo.database import Database


# ─── Credential-based helpers (existing, unchanged) ──────────────────────────

def create_mt5_credentials(db: Database, credentials_data: dict):
    if db.mt5_credentials.find_one({"account": str(credentials_data["account"])}):
        raise ValueError("Account already registered")
    db.mt5_credentials.insert_one(credentials_data)
    credentials_data.pop('_id', None)
    return credentials_data

def get_mt5_credentials(db: Database, user_id: str):
    creds = db.mt5_credentials.find_one({"user_id": user_id})
    if creds:
        creds.pop('_id', None)
    return creds

def get_mt5_credentials_by_account(db: Database, account: str):
    creds = db.mt5_credentials.find_one({"account": str(account)})
    if creds:
        creds.pop('_id', None)
    return creds

def update_mt5_credentials(db: Database, user_id: str, credentials_data: dict):
    result = db.mt5_credentials.update_one(
        {"user_id": user_id},
        {"$set": credentials_data}
    )
    if result.matched_count > 0:
        return get_mt5_credentials(db, user_id)
    return None

def delete_mt5_credentials(db: Database, user_id: str):
    result = db.mt5_credentials.delete_one({"user_id": user_id})
    return result.deleted_count > 0


# ─── EA / Token-based helpers (new) ──────────────────────────────────────────

def create_or_refresh_token(db: Database, user_id: str) -> dict:
    """
    Generate (or regenerate) a secure connection token for the user.
    Stored in the `mt5_connections` collection.
    """
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    record = {
        "user_id": user_id,
        "token": token,
        "created_at": now,
        "last_sync_at": None,
    }
    db.mt5_connections.update_one(
        {"user_id": user_id},
        {"$set": record},
        upsert=True
    )
    return record


def get_mt5_connection(db: Database, user_id: str) -> dict | None:
    """Get the EA connection record for a user."""
    record = db.mt5_connections.find_one({"user_id": user_id})
    if record:
        record.pop('_id', None)
    return record


def get_user_by_token(db: Database, token: str) -> str | None:
    """Look up the user_id associated with a token."""
    record = db.mt5_connections.find_one({"token": token})
    if record:
        return record.get("user_id")
    return None


def update_last_sync(db: Database, user_id: str):
    """Stamp the last successful EA sync time."""
    db.mt5_connections.update_one(
        {"user_id": user_id},
        {"$set": {"last_sync_at": datetime.now(timezone.utc)}}
    )


def delete_mt5_connection(db: Database, user_id: str) -> bool:
    """Remove the EA connection (disconnect)."""
    result = db.mt5_connections.delete_one({"user_id": user_id})
    return result.deleted_count > 0
