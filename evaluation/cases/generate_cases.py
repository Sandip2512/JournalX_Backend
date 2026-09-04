import os
import json
import random
from datetime import datetime, timedelta

benchmark_dir = os.path.dirname(os.path.abspath(__file__))

def create_trade(t_no, profit, sym, hrs_offset=1, vol=1.0, type="BUY"):
    t_open = datetime(2023, 1, 1) + timedelta(hours=hrs_offset)
    t_close = t_open + timedelta(minutes=30)
    return {
        "trade_no": t_no,
        "symbol": sym,
        "volume": vol,
        "type": type,
        "price_open": 1.0,
        "price_close": 1.0 if profit == 0 else (1.1 if profit > 0 and type == 'BUY' else 0.9),
        "net_profit": profit,
        "open_time": t_open.isoformat(),
        "close_time": t_close.isoformat(),
    }

cases = []

# Case 1: Overtrading after 3 trades/day.
# Scenario: Trades 1-3 are profitable, 4+ are losses.
case1 = []
day_offset = 0
t_no = 1
for day in range(10): # 10 days
    # first 3 wins
    for i in range(3):
        case1.append(create_trade(t_no, 50.0, "EURUSD", day_offset + i))
        t_no += 1
    # next 2 losses
    for i in range(3, 5):
        case1.append(create_trade(t_no, -60.0, "EURUSD", day_offset + i))
        t_no += 1
    day_offset += 24
cases.append({"id": 1, "pattern": "Overtrading after 3 trades/day.", "category": "Behavior", "trades": case1})

# Case 2: One instrument underperforms.
# XAUUSD loses consistently, others win.
case2 = []
for i in range(20):
    case2.append(create_trade(len(case2)+1, random.uniform(10, 50), "EURUSD", i*2))
    case2.append(create_trade(len(case2)+1, random.uniform(10, 50), "GBPUSD", i*2+1))
    case2.append(create_trade(len(case2)+1, random.uniform(-60, -20), "XAUUSD", i*2+2))
cases.append({"id": 2, "pattern": "One instrument underperforms (XAUUSD).", "category": "Instrument", "trades": case2})

# Case 3: Position size increases after losses (Martingale).
case3 = []
last_loss = False
vol = 1.0
count = 1
for i in range(30):
    if last_loss:
        vol *= 2 # doubled size
    else:
        vol = 1.0
        
    outcome = -50.0 if random.random() > 0.6 else 40.0
    case3.append(create_trade(count, outcome * vol, "EURUSD", i*5, vol=vol))
    last_loss = outcome < 0
    count += 1
cases.append({"id": 3, "pattern": "Position size increases after losses.", "category": "Risk", "trades": case3})

# Case 4: Performance deteriorates after consecutive losses.
case4 = []
seq_l = 0
for i in range(40):
    if seq_l >= 2:
        # tilted, always loss
        p = -50.0
        seq_l += 1
    else:
        p = 40.0 if random.random() > 0.4 else -40.0
        if p < 0:
            seq_l += 1
        else:
            seq_l = 0
    # Every 6 trades reset the tilt
    if i % 6 == 0:
        seq_l = 0
    case4.append(create_trade(i+1, p, "BTCUSD", i*2))
cases.append({"id": 4, "pattern": "Performance deteriorates after consecutive losses.", "category": "Behavior", "trades": case4})

# Generate empty 16 cases to reach 20 as requested for the benchmark
for x in range(5, 21):
    random_trades = []
    for i in range(20):
        random_trades.append(create_trade(i+1, random.uniform(-50, 50), random.choice(["EURUSD", "GBPUSD"]), i*3))
    cases.append({"id": x, "pattern": "No meaningful pattern.", "category": "None", "trades": random_trades})

# Save to disk
for case in cases:
    path = os.path.join(benchmark_dir, f"case_{case['id']}.json")
    with open(path, "w") as f:
        json.dump(case, f, indent=2)

print(f"Generated {len(cases)} test cases in {benchmark_dir}")
