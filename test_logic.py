import sys
import os
from datetime import datetime

# Add current directory to path so we can import app modules
sys.path.append(os.getcwd())

# Mock DB
class MockDB:
    def __init__(self):
        self.trades = self
        self.mistakes = self
        
        self.trade_data = [
            # Trade with multiple mistakes
            {
                "user_id": "1", 
                "mistake": "Overtrading, FOMO Entry",
                "close_time": datetime.utcnow()
            },
            # Trade with single mistake
            {
                "user_id": "1", 
                "mistake": "Revenge Trading",
                "close_time": datetime.utcnow()
            },
            # Trade with no mistakes
            {
                "user_id": "1", 
                "mistake": "No Mistake",
                "close_time": datetime.utcnow()
            }
        ]
        
        self.mistake_data = [
            # Custom mistake defined by user
            {
                "_id": "custom1",
                "name": "Overtrading",
                "category": "Psychological",
                "severity": "High", 
                "impact": "Critical",
                "user_id": "1"
            }
        ]

    def find(self, query):
        if "mistake" in query and "$ne" in query["mistake"]:
            # Logic for filtering trades with mistakes
            return [t for t in self.trade_data if t.get("mistake") and t.get("mistake") != "No Mistake"]
            
        if query.get("user_id"):
            # Return list based on collection context (inferred from call)
            # This is a simple mock, so we return what we think is asked based on context
            pass
            
        return [] 
        
    def find_one(self, query):
        name = query.get("name")
        for m in self.mistake_data:
            if m["name"] == name:
                return m
        return None

# Override find for specific calls simulation
class MockCollection:
    def __init__(self, data):
        self.data = data
        
    def find(self, query):
        return self.data
        
    def find_one(self, query):
        name = query.get("name")
        for d in self.data:
            if d.get("name") == name:
                return d
        return None

# Better Mock DB
class BetterMockDB:
    def __init__(self):
        self.trades_data = [
            {"user_id": "1", "mistake": "Overtrading, FOMO Entry", "close_time": datetime.utcnow()},
            {"user_id": "1", "mistake": "Revenge Trading", "close_time": datetime.utcnow()},
            {"user_id": "1", "mistake": "No Mistake", "close_time": datetime.utcnow()}
        ]
        self.mistakes_data = [
            {"_id": "custom1", "name": "Overtrading", "category": "Psychological", "severity": "High", "impact": "Critical", "user_id": "1", "created_at": None}
        ]
        
        self.trades = MockCollection(self.trades_data)
        self.mistakes = MockCollection(self.mistakes_data)

try:
    from app.crud.mistake_crud import get_mistake_analytics
    
    db = BetterMockDB()
    result = get_mistake_analytics(db, "1", "all")
    
    print("\n=== Analytics Result ===")
    print(f"Total Mistakes: {result['totalMistakes']}")
    print("Custom Mistakes List:")
    for m in result['customMistakes']:
        print(f"  - Name: '{m['name']}', Count: {m['count']}, Source: {'Custom' if m['id'] == 'custom1' else 'Auto'}")
        
    # Check if FOMO and Revenge are there
    names = [m['name'] for m in result['customMistakes']]
    
    if "Overtrading" in names and "FOMO Entry" in names and "Revenge Trading" in names:
        print("\n✅ SUCCESS: All mistakes (both custom and auto-generated) are found!")
    else:
        print("\n❌ FAILURE: Missing mistakes.")
        print(f"Found: {names}")
        
except ImportError as e:
    print(f"Import Error: {e}")
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
