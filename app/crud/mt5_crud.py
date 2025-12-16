from pymongo.database import Database

def create_mt5_credentials(db: Database, credentials_data: dict):
    # Check if account already exists
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
