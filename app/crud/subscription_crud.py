from pymongo.database import Database
import uuid
from datetime import datetime
from typing import List, Optional

# ------------------- Subscription CRUD -------------------

def get_subscription(db: Database, subscription_id: str):
    return db.subscriptions.find_one({"id": subscription_id})

def get_user_subscription(db: Database, user_id: str):
    # Source of truth is the User document
    user = db.users.find_one({"user_id": user_id})
    if not user:
        return None
        
    tier = (user.get("subscription_tier") or "free").lower()
    if tier == "free":
        return None
        
    return {
        "id": f"sub_{user_id}", # Virtual ID
        "user_id": user_id,
        "plan_name": tier.capitalize(),
        "status": "active", 
        "renewal_date": user.get("subscription_expiry"),
        "created_at": user.get("created_at")
    }

def create_subscription(db: Database, sub_data: dict):
    if "_id" in sub_data:
        sub_data.pop("_id")
    
    sub_data["id"] = str(uuid.uuid4())
    sub_data["created_at"] = datetime.now()
    
    db.subscriptions.insert_one(sub_data)
    
    # Create notification
    db.notifications.insert_one({
        "user_id": sub_data["user_id"],
        "title": "Subscription Activated",
        "content": f"Your {sub_data.get('plan_name', 'Premium')} subscription is now active!",
        "type": "personal",
        "is_read": False,
        "created_at": datetime.now()
    })
    
    return sub_data

def update_subscription(db: Database, sub_id: str, update_data: dict):
    db.subscriptions.update_one({"id": sub_id}, {"$set": update_data})
    return get_subscription(db, sub_id)

# ------------------- Transaction CRUD -------------------

def get_transaction(db: Database, transaction_id: str):
    # Check by custom 'id' first
    tx = db.transactions.find_one({"id": transaction_id})
    if tx:
        return tx
    
    # Try by MongoDB '_id'
    try:
        from bson.objectid import ObjectId
        tx = db.transactions.find_one({"_id": ObjectId(transaction_id)})
        if tx:
            return tx
    except Exception:
        pass
        
    return db.transactions.find_one({"_id": transaction_id})

def get_user_transactions(db: Database, user_id: str):
    transactions = list(db.transactions.find({"user_id": user_id}).sort("payment_date", -1))
    for tx in transactions:
        if not tx.get("id") and "_id" in tx:
            tx["id"] = str(tx["_id"])
    return transactions

def get_all_transactions(db: Database, skip: int = 0, limit: int = 100, filters: dict = None):
    query = filters or {}
    transactions = list(db.transactions.find(query).sort("payment_date", -1).skip(skip).limit(limit))
    for tx in transactions:
        if not tx.get("id") and "_id" in tx:
            tx["id"] = str(tx["_id"])
    return transactions

def create_transaction(db: Database, tx_data: dict):
    if "_id" in tx_data:
        tx_data.pop("_id")
    
    tx_data["id"] = str(uuid.uuid4())
    # Generate a simple invoice number if not provided
    if "invoice_number" not in tx_data:
        tx_data["invoice_number"] = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
    
    db.transactions.insert_one(tx_data)
    
    # If transaction is 'paid', notify user
    if tx_data.get("status") == "paid":
        db.notifications.insert_one({
            "user_id": tx_data["user_id"],
            "title": "Payment Successful",
            "content": f"Thank you! Your payment of ${tx_data.get('total_amount', 0):.2f} was successful.",
            "type": "personal",
            "is_read": False,
            "created_at": datetime.now()
        })
    
    return tx_data

def get_sales_analytics(db: Database):
    now = datetime.now()
    # This is a simplified version, ideally use aggregation pipeline
    all_tx = list(db.transactions.find({"status": "paid"}))
    
    total_rev = sum(tx["total_amount"] for tx in all_tx)
    active_subs = db.subscriptions.count_documents({"status": "active"})
    total_subs = db.subscriptions.count_documents({})
    
    # Plan breakdown
    plan_breakdown = {}
    for tx in all_tx:
        plan = tx.get("billing_details", {}).get("plan_name", "unknown")
        plan_breakdown[plan] = plan_breakdown.get(plan, 0) + tx["total_amount"]
        
    return {
        "total_revenue": total_rev,
        "monthly_revenue": total_rev / 12, # Placeholder
        "yearly_revenue": total_rev, # Placeholder
        "plan_breakdown": plan_breakdown,
        "total_subscribers": total_subs,
        "active_subscribers": active_subs
    }
