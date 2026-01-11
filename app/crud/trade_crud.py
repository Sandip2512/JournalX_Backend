from pymongo.database import Database
import pymongo

def create_trade(db: Database, trade_data: dict):
    # Calculate net profit if not provided
    if trade_data.get('net_profit') is None:
        trade_data['net_profit'] = trade_data.get('profit_amount', 0.0) - trade_data.get('loss_amount', 0.0)
    
    # Auto-generate trade_no if not provided
    if 'trade_no' not in trade_data or trade_data['trade_no'] is None:
        # Get max trade_no for THIS USER using aggregation
        pipeline = [
            {"$match": {"user_id": trade_data['user_id']}},
            {"$group": {"_id": None, "max_trade_no": {"$max": "$trade_no"}}}
        ]
        result = list(db.trades.aggregate(pipeline))
        max_trade_no = result[0]['max_trade_no'] if result else 0
        trade_data['trade_no'] = (max_trade_no or 0) + 1
    
    # Ensure trade_no is int
    trade_data['trade_no'] = int(trade_data['trade_no'])
    
    db.trades.insert_one(trade_data)
    # Return the inserted data (excluding _id for Pydantic compatibility if needed, though Pydantic can ignore it)
    trade_data.pop('_id', None)
    return trade_data

def get_trades(db: Database, user_id: str, skip: int = 0, limit: int = 100, sort_desc: bool = False):
    sort_dir = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING
    cursor = db.trades.find({"user_id": user_id}).sort("trade_no", sort_dir).skip(skip).limit(limit)
    trades = list(cursor)
    # Convert _id to string or remove it
    for t in trades:
        t.pop('_id', None)
    return trades

def get_trade_by_trade_no(db: Database, trade_no: int):
    trade = db.trades.find_one({"trade_no": trade_no})
    if trade:
        trade.pop('_id', None)
    return trade

def get_trade_by_ticket(db: Database, ticket: int):
    # Helper needed for MT5 service
    trade = db.trades.find_one({"ticket": ticket})
    if trade:
        trade.pop('_id', None)
    return trade

def delete_trade(db: Database, trade_no: int):
    result = db.trades.delete_one({"trade_no": trade_no})
    return result.deleted_count > 0

def update_trade_reason(db: Database, trade_no: int, reason: str, mistake: str):
    db.trades.update_one(
        {"trade_no": trade_no},
        {"$set": {"reason": reason, "mistake": mistake}}
    )
    return get_trade_by_trade_no(db, trade_no)
