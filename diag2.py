import sys; sys.path.insert(0, '.')
from app.mongo_database import get_db
db = get_db()
uid = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'
account = '433793931'
trades = list(db.trades.find({'user_id': uid}))

trades = [t for t in trades if str(t.get('mt5_account')) == account]

from collections import defaultdict
grouped = defaultdict(float)
types = defaultdict(int)

for t in trades:
    ptype = str(t.get('type'))
    np = float(t.get('net_profit', 0) or 0)
    grouped[ptype] += np
    types[ptype] += 1

print('Counts by type:', dict(types))
print('PNL by type:', dict(grouped))

trades.sort(key=lambda t: float(t.get('net_profit') or 0), reverse=True)
print('\nTop 5 Absolute Profit trades:')
for t in trades[:5]:
    print(f'  {t.get("type")} {t.get("symbol")} np={t.get("net_profit")} vol={t.get("volume")} p={t.get("price_open")}->{t.get("price_close")}')

# Also sort by lowest profit to check massive losses
trades.sort(key=lambda t: float(t.get('net_profit') or 0))
print('\nBottom 5 Absolute Profit trades:')
for t in trades[:5]:
    print(f'  {t.get("type")} {t.get("symbol")} np={t.get("net_profit")} vol={t.get("volume")} p={t.get("price_open")}->{t.get("price_close")}')

print("\nDuplicates grouped by ticket?")
from collections import Counter
tix = Counter([t.get("mt5_ticket") for t in trades if t.get("mt5_ticket")])
for k, v in tix.items():
    if v > 1:
        print(f" Ticket {k} duplicated {v} times")
