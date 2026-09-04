from datetime import datetime, timezone
from typing import List, Dict, Any
from app.services.ai_audit.contracts.schemas import NormalizedTrade, DataQualityStatus, DataQualityResult

def normalize_trade(raw: Dict[str, Any]) -> NormalizedTrade:
    """Safely normalizes raw MongoDB/Dict objects into normalized model."""
    trade_id = str(raw.get("_id") or raw.get("trade_no") or raw.get("ticket") or "UNKNOWN")
    
    # Dates
    o_time = raw.get("open_time")
    c_time = raw.get("close_time")
    
    # If string, try parse (simplified for robust production you'd use dateutil parser)
    if isinstance(o_time, str):
        try: o_time = datetime.fromisoformat(o_time.replace("Z", "+00:00"))
        except: o_time = None
    if isinstance(c_time, str):
        try: c_time = datetime.fromisoformat(c_time.replace("Z", "+00:00"))
        except: c_time = None
        
    holding_mins = 0.0
    if o_time and c_time:
        holding_mins = (c_time - o_time).total_seconds() / 60.0

    return NormalizedTrade(
        trade_id=trade_id,
        open_timestamp=o_time if o_time else datetime.min.replace(tzinfo=timezone.utc),
        close_timestamp=c_time if c_time else datetime.min.replace(tzinfo=timezone.utc),
        holding_time_minutes=holding_mins,
        symbol=str(raw.get("symbol", "UNKNOWN")),
        direction=str(raw.get("type", "UNKNOWN")).upper(),
        volume=float(raw.get("volume", 0.0)),
        open_price=float(raw.get("price_open", 0.0)),
        close_price=float(raw.get("price_close", 0.0)),
        net_profit=float(raw.get("net_profit", raw.get("profit_amount", 0) - raw.get("loss_amount", 0))),
        session=raw.get("session"),
        strategy=raw.get("strategy"),
        emotion=raw.get("emotion"),
        mistake=raw.get("mistake"),
        reason=raw.get("reason"),
    )

def cleanse_and_validate(raw_trades: List[Dict[str, Any]]) -> DataQualityResult:
    warnings = []
    valid = []
    seen_ids = set()
    
    if not raw_trades:
        return DataQualityResult(status=DataQualityStatus.INVALID, warnings=["Empty dataset."], valid_trades=[])
        
    for idx, raw in enumerate(raw_trades):
        try:
            trade = normalize_trade(raw)
        except Exception as e:
            warnings.append(f"Trade idx {idx} skipped: parsing error {e}")
            continue
            
        if trade.trade_id in seen_ids and trade.trade_id != "UNKNOWN":
            warnings.append(f"Trade {trade.trade_id} skipped: Duplicate")
            continue
            
        if trade.trade_id == "UNKNOWN":
            warnings.append(f"Trade missing ID at idx {idx}")
            continue
            
        if trade.open_timestamp == datetime.min.replace(tzinfo=timezone.utc) or trade.close_timestamp == datetime.min.replace(tzinfo=timezone.utc):
            warnings.append(f"Trade {trade.trade_id} skipped: Missing/Invalid timestamp")
            continue
            
        if trade.close_timestamp < trade.open_timestamp:
            warnings.append(f"Trade {trade.trade_id} skipped: Close time before open time")
            continue
            
        if trade.volume <= 0:
            warnings.append(f"Trade {trade.trade_id} skipped: Invalid volume")
            continue
            
        if trade.open_price < 0 or trade.close_price < 0:
            warnings.append(f"Trade {trade.trade_id} skipped: Invalid prices")
            continue

        if not trade.open_timestamp.tzinfo:
            warnings.append(f"Trade {trade.trade_id} timezone uncertain. Converted silently? No, leaving as naive.")
            # Phase 2 decision: do not silently assume UTC if unknown. We'll mark it to avoid session issues.
            # Python datetime without tzinfo is naive.
            
        seen_ids.add(trade.trade_id)
        valid.append(trade)
    
    if len(valid) == 0:
        status = DataQualityStatus.INVALID
        warnings.append("No valid trades remaining after cleansing.")
    elif len(valid) < 20:
        status = DataQualityStatus.INSUFFICIENT_DATA
        warnings.append("Less than 20 valid trades. Results may be unreliable.")
    elif len(warnings) > (len(valid) * 0.1):
        status = DataQualityStatus.WARNING
        warnings.insert(0, f"High error rate: {len(warnings)} warnings generated.")
    else:
        status = DataQualityStatus.VALID
        
    return DataQualityResult(status=status, warnings=warnings, valid_trades=valid)
