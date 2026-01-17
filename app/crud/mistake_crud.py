from pymongo.database import Database
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from bson import ObjectId

def _get_datetime(val):
    """Helper to ensure we have a datetime object or None"""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            # Handle ISO format strings if they exist
            return datetime.fromisoformat(val.replace('Z', '+00:00'))
        except:
            return None
    return None

def create_mistake(db: Database, mistake_data: dict):
    """Create a new custom mistake type"""
    mistake_data['created_at'] = datetime.utcnow()
    result = db.mistakes.insert_one(mistake_data)
    mistake_data['id'] = str(result.inserted_id)
    # Ensure id is string
    if '_id' in mistake_data:
        mistake_data.pop('_id')
    return mistake_data

def get_mistakes(db: Database, user_id: str):
    """Get all mistakes for a user with their occurrence counts from trades"""
    # Get custom mistakes
    custom_mistakes = list(db.mistakes.find({"user_id": user_id}))
    
    # Get all trades for the user
    trades = list(db.trades.find({"user_id": user_id}))
    
    # Count mistakes from trades (handle comma-separated values)
    mistake_counts = {}
    for trade in trades:
        mistake_str = trade.get("mistake", "")
        if mistake_str and mistake_str != "No Mistake":
            # Split by comma and strip whitespace
            mistakes = [m.strip() for m in mistake_str.split(",") if m.strip()]
            for mistake in mistakes:
                mistake_counts[mistake] = mistake_counts.get(mistake, 0) + 1
    
    # Create a dictionary of custom mistakes for quick lookup
    custom_mistake_dict = {m["name"]: m for m in custom_mistakes}
    
    # Build result list
    result = []
    
    # Add custom mistakes with their counts
    for mistake in custom_mistakes:
        mistake_name = mistake["name"]
        result.append({
            "id": str(mistake["_id"]),
            "name": mistake_name,
            "category": mistake["category"],
            "severity": mistake["severity"],
            "impact": mistake["impact"],
            "description": mistake.get("description", ""),
            "user_id": mistake["user_id"],
            "created_at": mistake.get("created_at"),
            "count": mistake_counts.get(mistake_name, 0)
        })
    
    # Add common mistakes from trades that aren't in custom mistakes
    common_mistakes_from_trades = set(mistake_counts.keys()) - set(custom_mistake_dict.keys())
    for mistake_name in common_mistakes_from_trades:
        # Auto-categorize common mistakes
        category = "Behavioral"
        severity = "Medium"
        impact = "Moderate"
        
        if "FOMO" in mistake_name or "Revenge" in mistake_name:
            category = "Psychological"
            severity = "High"
            impact = "Critical"
        elif "Ignored" in mistake_name or "No Clear Plan" in mistake_name:
            category = "Cognitive"
            severity = "High"
            impact = "Critical"
        elif "Exited" in mistake_name or "Late entry" in mistake_name:
            category = "Technical"
            severity = "Medium"
            impact = "Moderate"
        
        result.append({
            "id": f"auto-{str(mistake_name).replace(' ', '-').lower()}",
            "name": mistake_name,
            "category": category,
            "severity": severity,
            "impact": impact,
            "description": f"Auto-generated from trade data",
            "user_id": user_id,
            "created_at": None,
            "count": mistake_counts[mistake_name]
        })
    
    return result

def get_mistake_by_id(db: Database, mistake_id: str):
    """Get a single mistake by ID"""
    try:
        mistake = db.mistakes.find_one({"_id": ObjectId(mistake_id)})
        if mistake:
            mistake['id'] = str(mistake['_id'])
            mistake.pop('_id', None)
            
            # Get count from trades
            count = db.trades.count_documents({
                "user_id": mistake['user_id'],
                "mistake": mistake['name']
            })
            mistake['count'] = count
        return mistake
    except:
        return None

def update_mistake(db: Database, mistake_id: str, update_data: dict):
    """Update a mistake"""
    try:
        # Remove None values
        update_data = {k: v for k, v in update_data.items() if v is not None}
        
        if not update_data:
            return get_mistake_by_id(db, mistake_id)
        
        db.mistakes.update_one(
            {"_id": ObjectId(mistake_id)},
            {"$set": update_data}
        )
        return get_mistake_by_id(db, mistake_id)
    except:
        return None

def delete_mistake(db: Database, mistake_id: str):
    """Delete a mistake"""
    try:
        result = db.mistakes.delete_one({"_id": ObjectId(mistake_id)})
        return result.deleted_count > 0
    except:
        return False

def get_mistake_analytics(db: Database, user_id: str, time_filter: str = "all"):
    """Get analytics data for mistakes dashboard"""
    # Get all trades for the user
    query = {"user_id": user_id}
    
    # Apply time filter
    if time_filter == "month":
        from datetime import datetime, timedelta
        one_month_ago = datetime.utcnow() - timedelta(days=30)
        query["open_time"] = {"$gte": one_month_ago}
    
    trades = list(db.trades.find(query))
    
    # Count mistakes (handle comma-separated values)
    mistake_counts = {}
    category_counts = {"Behavioral": 0, "Psychological": 0, "Cognitive": 0, "Technical": 0}
    
    for trade in trades:
        mistake_str = trade.get("mistake", "")
        if mistake_str and mistake_str != "No Mistake":
            # Split by comma and strip whitespace
            mistakes = [m.strip() for m in mistake_str.split(",") if m.strip()]
            for mistake in mistakes:
                mistake_counts[mistake] = mistake_counts.get(mistake, 0) + 1
                
                # Categorize for distribution
                if "FOMO" in mistake or "Revenge" in mistake:
                    category_counts["Psychological"] += 1
                elif "Ignored" in mistake or "No Clear Plan" in mistake or "Not followed" in mistake:
                    category_counts["Cognitive"] += 1
                elif "Exited" in mistake or "Late entry" in mistake or "Risked" in mistake:
                    category_counts["Technical"] += 1
                else:
                    category_counts["Behavioral"] += 1
    
    # Calculate total mistakes
    total_mistakes = sum(mistake_counts.values())
    
    # Find most common mistake
    most_common = None
    if mistake_counts:
        most_common_name = max(mistake_counts, key=mistake_counts.get)
        most_common = {
            "name": most_common_name,
            "count": mistake_counts[most_common_name]
        }
    
    # Calculate improvement (placeholder - would need historical data)
    improvement = 0
    
    # Build distribution data - use individual mistakes as requested by user
    # Sort by count descending for better visualization
    sorted_mistakes = sorted(mistake_counts.items(), key=lambda x: x[1], reverse=True)
    
    distribution = [
        {"category": name, "count": count} 
        for name, count in sorted_mistakes[:10]  # Limit to top 10 for cleaner chart
    ]
    
    # Get custom mistakes with counts
    custom_mistakes = get_mistakes(db, user_id)
    
    return {
        "totalMistakes": total_mistakes,
        "mostCommon": most_common,
        "improvement": improvement,
        "distribution": distribution,
        "customMistakes": custom_mistakes
    }

def get_frequency_heatmap_data(db: Database, user_id: str, days: int = 35):
    """Get frequency heatmap data for the last N days"""
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get all trades with mistakes in the date range
    trades = list(db.trades.find({
        "user_id": user_id,
        "mistake": {"$exists": True, "$ne": "", "$ne": "No Mistake"},
        "close_time": {"$gte": start_date, "$lte": end_date}
    }))
    
    # Count mistakes per day (handle comma-separated values)
    daily_counts = {}
    for trade in trades:
        # Robustly handle close_time
        close_time = _get_datetime(trade.get('close_time'))
        if not close_time:
            continue
            
        date_str = close_time.strftime('%Y-%m-%d')
        mistake_str = trade.get("mistake", "")
        if mistake_str and mistake_str != "No Mistake":
            # Split by comma and count each mistake
            mistakes = [m.strip() for m in mistake_str.split(",") if m.strip()]
            # Count the number of mistakes in this trade for this day
            daily_counts[date_str] = daily_counts.get(date_str, 0) + len(mistakes)
    
    # Generate all dates in range
    heatmap_data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        heatmap_data.append({
            "date": date_str,
            "count": daily_counts.get(date_str, 0)
        })
        current_date += timedelta(days=1)
    
    return heatmap_data
