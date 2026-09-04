import requests
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8001/api/backtest"
USER_ID = "test_user_ai" # For testing purposes

def test_backtest_flow():
    # 1. Create Session
    session_payload = {
        "strategy_name": "Test Strategy",
        "pairs": ["BTCUSDT"],
        "timeframe": "1h",
        "start_date": (datetime.now() - timedelta(days=7)).isoformat(),
        "end_date": datetime.now().isoformat(),
        "starting_balance": 10000,
        "mode": "backtest"
    }
    
    print("Creating session...")
    response = requests.post(f"{BASE_URL}/sessions?user_id={USER_ID}", json=session_payload)
    if response.status_code != 200:
        print(f"Failed to create session: {response.text}")
        return
    
    session = response.json()
    session_id = session["_id"]
    print(f"Created session with ID: {session_id}")

    # 2. Record Trade
    trade_payload = {
        "session_id": session_id,
        "pair": "BTCUSDT",
        "entry_time": (datetime.now() - timedelta(days=1)).isoformat(),
        "entry_price": 50000.0,
        "lot_size": 0.1,
        "trade_type": "buy",
        "status": "open"
    }
    
    print("Recording trade...")
    response = requests.post(f"{BASE_URL}/trades?user_id={USER_ID}", json=trade_payload)
    trade = response.json()
    trade_id = trade["_id"]
    print(f"Recorded trade with ID: {trade_id}")

    # 3. Update (Close) Trade
    close_payload = {
        "status": "closed",
        "exit_price": 51000.0,
        "exit_time": datetime.now().isoformat()
    }
    
    print("Closing trade...")
    response = requests.patch(f"{BASE_URL}/trades/{trade_id}", json=close_payload)
    closed_trade = response.json()
    print(f"Closed trade with PL: {closed_trade['profit_loss']}")

    # 4. Get Stats
    print("Getting stats...")
    response = requests.get(f"{BASE_URL}/sessions/{session_id}/stats")
    stats = response.json()
    print(f"Stats: {json.dumps(stats, indent=2)}")

if __name__ == "__main__":
    test_backtest_flow()
