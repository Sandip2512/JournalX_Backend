from pymongo.database import Database
import pymongo
from app.crud.rules_crud import evaluate_trade_compliance

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
    
    # Evaluate compliance before inserting
    compliance_flags = evaluate_trade_compliance(db, trade_data['user_id'], trade_data)
    trade_data.update(compliance_flags)

    db.trades.insert_one(trade_data)
    # Return the inserted data (excluding _id for Pydantic compatibility if needed, though Pydantic can ignore it)
    trade_data.pop('_id', None)
    return trade_data

def get_trades(db: Database, user_id: str, skip: int = 0, limit: int = 10000, sort_desc: bool = False, active_account: str = None):
    sort_dir = pymongo.DESCENDING if sort_desc else pymongo.ASCENDING
    query = {"user_id": user_id}
    if active_account:
        # Connected: show ONLY this account's trades plus manual trades
        try:
            int_account = int(active_account)
        except (ValueError, TypeError):
            int_account = None
        or_clauses = [
            {"mt5_account": active_account},
            {"mt5_account": {"$in": [None, ""]}},
            {"mt5_account": {"$exists": False}}
        ]
        if int_account is not None:
            or_clauses.append({"mt5_account": int_account})
        query["$or"] = or_clauses
    else:
        # Disconnected: return ONLY manual trades
        query["$or"] = [
            {"mt5_account": {"$in": [None, ""]}},
            {"mt5_account": {"$exists": False}}
        ]
    cursor = db.trades.find(query).sort("trade_no", sort_dir).skip(skip).limit(limit)
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

def update_trade_journal(db: Database, trade_no: int, journal_data: dict):
    # Ensure nested updates or just flat fields
    db.trades.update_one(
        {"trade_no": trade_no},
        {"$set": journal_data}
    )
    return get_trade_by_trade_no(db, trade_no)

def update_trade(db: Database, trade_no: int, trade_data: dict):
    db.trades.update_one(
        {"trade_no": trade_no},
        {"$set": trade_data}
    )
    return get_trade_by_trade_no(db, trade_no)
