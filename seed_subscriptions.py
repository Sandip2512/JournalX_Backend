from pymongo import MongoClient
import os
from datetime import datetime, timedelta
import uuid

# Configuration
MONGO_URI = "mongodb+srv://sandipsunny2512:Sandip2512@cluster0.z5i6z.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "JournalX"

def seed_data():
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Get an admin and a regular user
    admin = db.users.find_one({"role": "admin"})
    user = db.users.find_one({"role": "user"})
    
    if not user:
        print("No user found to seed subscriptions for.")
        return

    # Seed Subscriptions
    sub_data = {
        "id": str(uuid.uuid4()),
        "user_id": user["user_id"],
        "plan_name": "yearly",
        "status": "active",
        "price": 199.99,
        "currency": "USD",
        "start_date": datetime.now() - timedelta(days=30),
        "renewal_date": datetime.now() + timedelta(days=335),
        "created_at": datetime.now()
    }
    db.subscriptions.delete_many({"user_id": user["user_id"]})
    db.subscriptions.insert_one(sub_data)
    print(f"✅ Seeded subscription for {user['email']}")

    # Seed Transactions
    txs = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "invoice_number": f"INV-2025-001",
            "amount": 180.00,
            "tax_amount": 19.99,
            "total_amount": 199.99,
            "currency": "USD",
            "payment_method": "Credit Card",
            "status": "paid",
            "payment_date": datetime.now() - timedelta(days=30),
            "billing_details": {
                "full_name": f"{user['first_name']} {user['last_name']}",
                "email": user["email"],
                "address": "123 Main St, New York, NY",
                "plan_name": "Yearly Premium"
            }
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user["user_id"],
            "invoice_number": f"INV-2025-002",
            "amount": 15.00,
            "tax_amount": 1.50,
            "total_amount": 16.50,
            "currency": "USD",
            "payment_method": "PayPal",
            "status": "paid",
            "payment_date": datetime.now() - timedelta(days=60),
            "billing_details": {
                "full_name": f"{user['first_name']} {user['last_name']}",
                "email": user["email"],
                "address": "123 Main St, New York, NY",
                "plan_name": "Monthly Add-on"
            }
        }
    ]
    db.transactions.delete_many({"user_id": user["user_id"]})
    db.transactions.insert_many(txs)
    print(f"✅ Seeded {len(txs)} transactions for {user['email']}")

if __name__ == "__main__":
    seed_data()
