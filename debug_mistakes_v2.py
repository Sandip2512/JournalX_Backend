from pymongo import MongoClient
import sys

try:
    # Connect to MongoDB using 127.0.0.1
    client = MongoClient('mongodb://127.0.0.1:27017/', serverSelectionTimeoutMS=2000)
    db = client['trading_journal']
    
    # Check connection
    client.server_info()
    print("Connected to MongoDB successfully!")

    # Get recent trades with mistakes
    trades = list(db.trades.find({'user_id': '1'}).sort('trade_no', -1).limit(5))

    print("\n=== Recent Trades ===")
    for trade in trades:
        print(f"Trade #{trade.get('trade_no')}")
        print(f"  Mistake Raw: '{trade.get('mistake', 'N/A')}'")

    # Check custom mistakes
    custom_mistakes = list(db.mistakes.find({'user_id': '1'}))
    print(f"\n=== Custom Mistakes in DB: {len(custom_mistakes)} ===")
    for m in custom_mistakes:
        print(f"  - {m.get('name')}")

except Exception as e:
    print(f"Error: {e}")
