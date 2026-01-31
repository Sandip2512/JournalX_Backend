from pymongo.database import Database
from datetime import datetime, timedelta
from typing import Optional

def create_coupon(db: Database, coupon_data: dict):
    coupon_data["created_at"] = datetime.utcnow()
    coupon_data["times_used"] = 0
    coupon_data["is_active"] = True
    return db.coupons.insert_one(coupon_data)

def get_coupon(db: Database, code: str):
    return db.coupons.find_one({"code": code, "is_active": True})

def redeem_coupon(db: Database, user_id: str, code: str) -> dict:
    coupon = db.coupons.find_one({"code": code})
    
    if not coupon:
        return {"success": False, "message": "Invalid coupon code"}
    
    if not coupon.get("is_active", True):
        return {"success": False, "message": "Coupon is inactive"}

    if coupon.get("max_uses") and coupon.get("times_used", 0) >= coupon["max_uses"]:
        return {"success": False, "message": "Coupon usage limit reached"}
        
    # Valid coupon
    new_usage = coupon.get("times_used", 0) + 1
    db.coupons.update_one({"_id": coupon["_id"]}, {"$set": {"times_used": new_usage}})
    
    # Calculate expiry
    duration = coupon.get("duration_days", 30)
    expiry = datetime.utcnow() + timedelta(days=duration)
    
    # Update user
    user = db.users.find_one({"user_id": user_id})
    db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "subscription_tier": coupon["tier"],
                "subscription_expiry": expiry
            }
        }
    )

    # Create Transaction Record
    import uuid
    
    # Define plan prices
    plan_prices = {
        "pro": 5.99,
        "elite": 11.99
    }
    plan_price = plan_prices.get(coupon["tier"], 0.0)
    
    transaction_data = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "payment_date": datetime.utcnow(),
        "total_amount": plan_price,  # Show actual plan value
        "discount_amount": plan_price,  # 100% discount via coupon
        "amount_paid": 0.0,  # Nothing paid
        "status": "paid",
        "invoice_number": f"INV-{datetime.utcnow().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}",
        "billing_details": {
            "plan_name": coupon["tier"],
            "payment_method": "coupon",
            "coupon_code": code,
            "full_name": f"{user.get('first_name', '')} {user.get('last_name', '')}".strip() or "Valued Member",
            "email": user.get('email', '')
        }
    }
    db.transactions.insert_one(transaction_data)
    
    return {
        "success": True, 
        "message": f"Upgraded to {coupon['tier'].title()}",
        "tier": coupon["tier"],
        "expiry": expiry
    }
