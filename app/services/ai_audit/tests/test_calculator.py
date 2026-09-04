import unittest
from datetime import datetime, timezone, timedelta
from app.services.ai_audit.contracts.schemas import NormalizedTrade, SampleSizeCategory
from app.services.ai_audit.tools.calculator import compute_metrics, analyze_sequences, analyze_overtrading, full_analytics
from app.services.ai_audit.tools.cleansing import cleanse_and_validate, DataQualityStatus

def tf_now(mins=0):
    return datetime(2023, 1, 1, tzinfo=timezone.utc) + timedelta(minutes=mins)

def create_trade(net, mins_offset=0, vol=1.0, sym="EURUSD"):
    return NormalizedTrade(
        trade_id=f"T{mins_offset}",
        open_timestamp=tf_now(mins_offset),
        close_timestamp=tf_now(mins_offset+5),
        holding_time_minutes=5.0,
        symbol=sym,
        direction="BUY",
        volume=vol,
        open_price=1.0,
        close_price=1.1,
        net_profit=net
    )

class TestDeterministicAnalytics(unittest.TestCase):
    
    def test_empty_dataset(self):
        m = compute_metrics([])
        self.assertEqual(m.total_trades, 0)
        self.assertEqual(m.sample_size_category, SampleSizeCategory.VERY_SMALL)

    def test_all_winning(self):
        trades = [create_trade(10, i) for i in range(10)]
        m = compute_metrics(trades)
        self.assertEqual(m.winning_trades, 10)
        self.assertEqual(m.losing_trades, 0)
        self.assertEqual(m.win_rate, 100.0)
        self.assertEqual(m.profit_factor, 999.0)
        self.assertEqual(m.maximum_drawdown, 0.0)
        self.assertEqual(len(m.trade_ids), 10)

    def test_all_losing(self):
        trades = [create_trade(-10, i) for i in range(10)]
        m = compute_metrics(trades)
        self.assertEqual(m.win_rate, 0.0)
        self.assertEqual(m.profit_factor, 0.0)
        
    def test_sequences_and_drawdown(self):
        # 1: win 10, 2: loss -20, 3: loss -10, 4: win 50
        t1 = create_trade(10, 0)
        t2 = create_trade(-20, 10)
        t3 = create_trade(-10, 20)
        t4 = create_trade(50, 30)
        m = compute_metrics([t1, t2, t3, t4])
        self.assertEqual(m.maximum_drawdown, 30.0) # peak 10, drops to -20 (dd 30)
        
        seq = analyze_sequences([t1, t2, t3, t4])
        # After loss: t3 (after t2), t4 (after t3)
        self.assertEqual(seq.after_loss.total_trades, 2)
        # Cons losses 2: t3
        self.assertEqual(seq.consecutive_losses_2.total_trades, 1)

    def test_cleansing_validation(self):
        raw = [
            {"_id": "1", "symbol": "A", "type":"BUY", "volume": 1.0, "price_open": 1, "price_close": 2, "net_profit": 10, "open_time": "2023-01-01T00:00:00Z", "close_time": "2023-01-01T00:05:00Z"},
            {"_id": "1", "symbol": "A"} # Duplicate + invalid
        ]
        res = cleanse_and_validate(raw)
        self.assertEqual(len(res.valid_trades), 1)
        self.assertTrue(len(res.warnings) > 0)

    def test_full_analytics(self):
        t1 = create_trade(10, 0, sym="GBPUSD") # trade 1 in day
        t2 = create_trade(-10, 10, vol=2.0)    # trade 2 in day
        t3 = create_trade(50, 60*24)           # trade 1 in next day
        
        full = full_analytics([t1, t2, t3])
        self.assertTrue("GBPUSD" in full.symbols)
        self.assertTrue("EURUSD" in full.symbols)
        self.assertEqual(full.overtrading.trade_1.total_trades, 2) # t1 and t3
        self.assertEqual(full.position_sizing.average_volume, 1.33)

if __name__ == '__main__':
    unittest.main()
