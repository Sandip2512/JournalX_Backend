from pymongo.database import Database
from datetime import datetime
import uuid
from typing import Optional, Dict, Any, List
from app.schemas.rules_schema import TradingRulesCreate, TradingRulesUpdate

COLLECTION_NAME = "rules"

def _get_current_month() -> str:
    return datetime.utcnow().strftime("%Y-%m")

def get_rules_for_month(db: Database, user_id: str, month: str = None) -> Optional[Dict[str, Any]]:
    if not month:
        month = _get_current_month()
        
    # Get the latest version for the month
    rules = list(db[COLLECTION_NAME].find({"user_id": user_id, "month": month}).sort("version", -1).limit(1))
    if rules:
        r = rules[0]
        r["_id"] = str(r["_id"])
        return r
    return None

def create_or_update_rules(db: Database, user_id: str, rules_data: TradingRulesCreate | TradingRulesUpdate, month: str = None) -> Dict[str, Any]:
    if not month:
        month = _get_current_month()
        
    current_rules = get_rules_for_month(db, user_id, month)
    version = 1
    
    if current_rules:
        version = current_rules.get("version", 0) + 1
        
    new_rule = {
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "month": month,
        "version": version,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    # Merge existing rules with updates if updating
    if isinstance(rules_data, TradingRulesUpdate) and current_rules:
        merged = current_rules.copy()
        update_dict = rules_data.model_dump(exclude_unset=True)
        merged.update(update_dict)
        for k in ["_id", "id", "user_id", "month", "version", "created_at"]:
            merged.pop(k, None)
        new_rule.update(merged)
    else:
        new_rule.update(rules_data.model_dump())
        
    db[COLLECTION_NAME].insert_one(new_rule)
    new_rule.pop("_id", None)
    return new_rule

def copy_last_month_rules(db: Database, user_id: str) -> Optional[Dict[str, Any]]:
    current_month = _get_current_month()
    
    # Check if already exists for current month
    if get_rules_for_month(db, user_id, current_month):
        return get_rules_for_month(db, user_id, current_month)
        
    # Find the most recent rules
    last_rules = list(db[COLLECTION_NAME].find({"user_id": user_id}).sort("created_at", -1).limit(1))
    if not last_rules:
        return None
        
    prev_rules = last_rules[0]
    
    # Create new rule object based on prev rules
    create_schema = TradingRulesCreate(
        max_risk_per_trade=prev_rules.get("max_risk_per_trade", 2.0),
        max_daily_loss=prev_rules.get("max_daily_loss", 5.0),
        max_trades_per_day=prev_rules.get("max_trades_per_day", 5),
        max_losing_trades=prev_rules.get("max_losing_trades", 3),
        risk_reward=prev_rules.get("risk_reward", "1:2"),
        sessions=prev_rules.get("sessions", []),
        pairs=prev_rules.get("pairs", [])
    )
    
    return create_or_update_rules(db, user_id, create_schema, current_month)
    
# ---- Engine ----

def evaluate_trade_compliance(db: Database, user_id: str, trade_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates a trade against the current month's rules.
    Returns a dictionary of compliance flags to be merged into the trade data.
    """
    if "open_time" not in trade_data:
        return {}
        
    trade_date = trade_data["open_time"]
    if isinstance(trade_date, str):
        try:
            trade_date = datetime.fromisoformat(trade_date.replace('Z', '+00:00'))
        except:
            trade_date = datetime.utcnow()
            
    month_str = trade_date.strftime("%Y-%m")
    rules = get_rules_for_month(db, user_id, month_str)
    
    if not rules:
        return {}
        
    flags = {
        "followed_risk": True,
        "followed_daily_loss": True,
        "followed_trade_limit": True,
        "followed_rules": True
    }
    
    # 1. Risk Compliance (Needs balance data to be accurate, but we use risk_percentage if available from frontend)
    if "risk_percentage" in trade_data and trade_data["risk_percentage"] is not None:
        if trade_data["risk_percentage"] > rules.get("max_risk_per_trade", 999):
            flags["followed_risk"] = False

    # Calculate daily stats to evaluate daily loss/trades limits
    start_of_day = trade_date.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day = trade_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    daily_trades = list(db.trades.find({
        "user_id": user_id,
        "open_time": {"$gte": start_of_day, "$lte": end_of_day}
    }))
    
    # 2. Daily Trade Limit
    if len(daily_trades) >= rules.get("max_trades_per_day", 999):
        flags["followed_trade_limit"] = False
        
    # 3. Daily Loss Limit (Sum of losses today + this trade's loss)
    # this requires us to estimate balance. If loss limit is %, it's hard without an account balance.
    # We will assume loss limit is an absolute $ amount if > 100, else % of something.
    # For now, we will track total daily loss amount, and if the user hit max_losing_trades instead.
    losing_trades_count = sum(1 for t in daily_trades if t.get("profit_amount", 0) - t.get("loss_amount", 0) < 0)
    if trade_data.get("profit_amount", 0) - trade_data.get("loss_amount", 0) < 0:
         losing_trades_count += 1
         
    if losing_trades_count > rules.get("max_losing_trades", 999):
        flags["followed_daily_loss"] = False

    flags["followed_rules"] = all(flags.values())
    return flags
