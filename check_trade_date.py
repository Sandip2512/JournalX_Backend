import pymongo
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

client = pymongo.MongoClient(os.getenv("MONGODB_URL"))
db = client.get_database("trading_journal")
trades = db.get_collection("trades")

# Find the most recent trade or search for one with "BTC/USD"
latest_trade = trades.find_one({"symbol": "BTC/USD"}, sort=[("_id", -1)])

if latest_trade:
    print(f"ID: {latest_trade['_id']}")
    print(f"Symbol: {latest_trade['symbol']}")
    print(f"Open Time (Raw): {latest_trade.get('open_time')}")
    print(f"Open Time Type: {type(latest_trade.get('open_time'))}")
else:
    print("No trade found.")
