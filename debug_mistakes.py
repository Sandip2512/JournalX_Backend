from pymongo import MongoClient

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['trading_journal']

# Get recent trades with mistakes
trades = list(db.trades.find({'user_id': '1'}).sort('trade_no', -1).limit(5))

print("=== Recent Trades ===")
for trade in trades:
    print(f"\nTrade #{trade.get('trade_no')}")
    print(f"  Symbol: {trade.get('symbol')}")
    print(f"  Mistake: '{trade.get('mistake', 'N/A')}'")
    print(f"  Type: {type(trade.get('mistake'))}")

# Check if there are any mistakes at all
total_with_mistakes = db.trades.count_documents({
    'user_id': '1',
    'mistake': {'$exists': True, '$ne': '', '$ne': 'No Mistake'}
})

print(f"\n=== Total trades with mistakes: {total_with_mistakes} ===")

# Check custom mistakes
custom_mistakes = list(db.mistakes.find({'user_id': '1'}))
print(f"\n=== Custom Mistakes in DB: {len(custom_mistakes)} ===")
for m in custom_mistakes:
    print(f"  - {m.get('name')} ({m.get('category')})")
