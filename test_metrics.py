import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_audit.tools.trading_metrics import calculate_basic_metrics, analyze_sequence, analyze_by_instrument
from app.services.ai_audit.schemas.ai_audit_schema import AgentTradeInput
from datetime import datetime
import json

def test_metrics():
    # Load Case 1
    with open("evaluation/cases/case_1.json", "r") as f:
        data = json.load(f)
        
    trades = [AgentTradeInput(**t) for t in data['trades']]
    
    basic = calculate_basic_metrics(trades)
    print("Base:", basic)
    assert basic.total_trades == 50
    assert basic.win_rate == 60.0
    
    inst = analyze_by_instrument(trades)
    print("Instrument:", inst)
    
    seq = analyze_sequence(trades)
    print("Seq:", seq)
    
    print("Metrics tests passed.")

if __name__ == "__main__":
    test_metrics()
