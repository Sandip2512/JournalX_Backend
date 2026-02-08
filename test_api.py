import requests

def test_binance():
    url = "https://api-gcp.binance.com/api/v3/klines"
    params = {
        "symbol": "BTCUSDT",
        "interval": "1h",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"Binance Status: {r.status_code}")
        print(f"Binance Data: {r.json()[:1]}")
    except Exception as e:
        print(f"Binance Error: {e}")

def test_kucoin():
    url = "https://api.kucoin.com/api/v1/market/candles"
    params = {
        "symbol": "BTC-USDT",
        "type": "1hour",
        "limit": 1
    }
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"KuCoin Status: {r.status_code}")
        print(f"KuCoin Data: {r.json().get('data', [])[:1]}")
    except Exception as e:
        print(f"KuCoin Error: {e}")

test_binance()
test_kucoin()
