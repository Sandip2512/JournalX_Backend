import os
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

def check_coupons():
    uri = os.getenv("MONGO_URI")
    db_name = os.getenv("DB_NAME", "JournalX")
    
    print(f"📡 Connecting to: {uri.split('@')[-1]}")
    
    try:
        client = MongoClient(uri)
        db = client[db_name]
        
        coupons = list(db.coupons.find({}))
        print(f"📊 Found {len(coupons)} coupons")
        
        for c in coupons:
            code = c.get('code', 'N/A')
            tier = c.get('tier', 'N/A')
            active = c.get('is_active', True)
            print(f"- Code: {code} | Tier: {tier} | Active: {active}")
            
    except Exception as e:
        print(f"❌ Error: {str(e)}")

if __name__ == "__main__":
    check_coupons()
