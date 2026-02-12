import requests

API_KEY = "d0sa91pr01qkkplu0drgd0sa91pr01qkkplu0ds0"
SYMBOL = "AAPL"
URL = f"https://finnhub.io/api/v1/quote"

def verify_key():
    params = {
        "symbol": SYMBOL,
        "token": API_KEY
    }
    
    print(f"Verifying API key with quote for {SYMBOL}...")
    try:
        response = requests.get(URL, params=params)
        print(f"Status Code: {response.status_code}")
        print("Response:", response.json())
        
        if response.status_code == 200:
            print("API Key is VALID.")
        else:
            print("API Key is INVALID or restricted.")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_key()
