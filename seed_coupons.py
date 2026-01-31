from pymongo import MongoClient
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "JournalX")

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

def seed_coupons():
    coupons = [
        {
            "code": "PRO2025",
            "tier": "pro",
            "duration_days": 30,
            "max_uses": 100,
            "times_used": 0,
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "code": "ELITE2025",
            "tier": "elite",
            "duration_days": 30,
            "max_uses": 50,
            "times_used": 0,
            "is_active": True,
            "created_at": datetime.utcnow()
        },
        {
            "code": "WELCOME_OFFER",
            "tier": "pro",
            "duration_days": 7,
            "max_uses": 1000,
            "times_used": 0,
            "is_active": True,
            "created_at": datetime.utcnow()
        }
    ]

    print(f"🌱 Seeding {len(coupons)} coupons...")
    
    for coupon in coupons:
        result = db.coupons.update_one(
            {"code": coupon["code"]},
            {"$set": coupon},
            upsert=True
        )
        if result.upserted_id:
            print(f"   Created: {coupon['code']}")
        else:
            print(f"   Updated: {coupon['code']}")

    print("✅ Coupon seeding complete!")

if __name__ == "__main__":
    seed_coupons()
