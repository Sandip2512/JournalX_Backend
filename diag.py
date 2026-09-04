import sys; sys.path.insert(0, '.')
from app.mongo_database import get_db
db = get_db()
uid = 'e5a933cf-d99e-4b85-a2ff-379efbe82e0b'
account = '433793931'

trades = list(db.trades.find({'user_id': uid, 'mt5_account': account}))
print(f'Unique trades for account {account}: {len(trades)}')

# Compute totals
total_np = sum(float(t.get('net_profit') or 0) for t in trades)
wins = [t for t in trades if float(t.get('net_profit') or 0) > 0]
losses = [t for t in trades if float(t.get('net_profit') or 0) < 0]
print(f'Total Net Profit: ${total_np:.2f}')
print(f'Wins: {len(wins)}, Losses: {len(losses)}')

# Date range
dates = []
for t in trades:
    for field in ['close_time', 'open_time']:
        v = t.get(field)
        if v:
            dates.append(str(v)[:10])
            break
if dates:
    dates.sort()
    print(f'Date range: {dates[0]} to {dates[-1]}')

# Check if any trades have mt5_ticket (EA sync) vs no ticket (old fetch)
with_ticket = [t for t in trades if t.get('mt5_ticket')]
without_ticket = [t for t in trades if not t.get('mt5_ticket')]
print(f'EA-synced (has mt5_ticket): {len(with_ticket)}')
print(f'Old-fetch (no mt5_ticket):  {len(without_ticket)}')
if without_ticket:
    old_np = sum(float(t.get('net_profit') or 0) for t in without_ticket)
    print(f'Net profit from old-fetch trades: ${old_np:.2f}')
