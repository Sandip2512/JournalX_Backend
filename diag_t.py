from pymongo import MongoClient

def main():
    client = MongoClient('mongodb://localhost:27017')
    db = client['journalx']
    
    user = db.users.find_one({'email': 'sandipsalunkhe6640@gmail.com'})
    user_id = user['user_id']
    
    trades = list(db.trades.find({'user_id': user_id}))
    mt5_trades = [t for t in trades if t.get('is_mt5_sync')]
    
    print(f"User: {user['email']}, user_id: {user_id}")
    print(f"Total trades: {len(trades)}")
    print(f"Total MT5 trades: {len(mt5_trades)}")
    
    from collections import Counter
    accounts = Counter([str(t.get('mt5_account')) for t in mt5_trades])
    print(f"Account distribution: {accounts}")

if __name__ == '__main__':
    main()
