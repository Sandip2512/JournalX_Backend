from app.mongo_database import db_client
from datetime import datetime
import sys

# Connect
print("🔌 Connecting to Database...")
try:
    db = db_client.connect()
except Exception as e:
    print(f"❌ Connection failed: {e}")
    sys.exit(1)

code = "ELITE2025"
print(f"🔍 Checking coupon: {code}")

coupon = db.coupons.find_one({"code": code})
if coupon:
    print("✅ Coupon found!")
    print(f"   Tier: {coupon.get('tier')}")
    print(f"   Max Uses: {coupon.get('max_uses')}")
    print(f"   Times Used: {coupon.get('times_used')}")
    print(f"   Expires: {coupon.get('expires_at')}")
    print(f"   Is Active: {coupon.get('is_active')}")
    
    # Check logic from redeem_coupon
    if not coupon.get("is_active", True):
        print("❌ FAIL: Coupon is inactive")
        
    if coupon.get("max_uses") and coupon.get("times_used", 0) >= coupon["max_uses"]:
        print("❌ FAIL: Coupon usage limit reached")
        
    if coupon.get('expires_at') and coupon.get('expires_at') < datetime.utcnow():
        print("❌ FAIL: Coupon EXPIRED")
        
    print("🎉 Coupon should be VALID")
else:
    print("❌ Coupon NOT found in database")
    # List all coupons to see what exists
    print("📋 Listing all coupons:")
    for c in db.coupons.find():
        print(f"   - {c.get('code')} ({c.get('tier')})")
