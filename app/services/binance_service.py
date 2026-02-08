import logging
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class BinanceService:
    # Multiple endpoints to bypass geoblocking (api-gcp is usually best for Vercel)
    BASE_URLS = [
        "https://api-gcp.binance.com", 
        "https://api1.binance.com",
        "https://api2.binance.com",
        "https://api3.binance.com",
        "https://api.binance.com"
    ]
    
    KUCOIN_URL = "https://api.kucoin.com/api/v1/market/candles"
    
    # Mapping for common symbols to Binance symbols
    SYMBOL_MAPPING = {
        "XAU/USD": "PAXGUSDT",
        "BTC/USD": "BTCUSDT",
        "ETH/USD": "ETHUSDT",
        "GBP/USD": "GBPUSDT",
        "EUR/USD": "EURUSDT",
        "JPY/USD": "USDJPY",
        "USD/JPY": "USDJPY",
    }

    @classmethod
    def get_klines_sync(
        cls, 
        symbol: str, 
        interval: str = "1h", 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None, 
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Synchronous kline fetch using requests with multiple fallback endpoints.
        """
        binance_symbol = cls.SYMBOL_MAPPING.get(symbol, symbol.replace("/", "").replace(" ", ""))
        
        params = {
            "symbol": binance_symbol,
            "interval": interval,
            "limit": limit
        }
        if start_time: params["startTime"] = start_time
        if end_time: params["endTime"] = end_time

        # 1. Try Binance Endpoints
        last_error = ""
        for base_url in cls.BASE_URLS:
            try:
                response = requests.get(f"{base_url}/api/v3/klines", params=params, timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    if data and len(data) > 0:
                        return data
                    last_error = "Binance returned empty data"
                
                # If it's a symbol error, don't retry other endpoints
                if response.status_code == 400 and "Invalid symbol" in response.text:
                    if "USD" in binance_symbol and "USDT" not in binance_symbol:
                        params["symbol"] = binance_symbol.replace("USD", "USDT")
                        retry_response = requests.get(f"{base_url}/api/v3/klines", params=params, timeout=5)
                        if retry_response.status_code == 200:
                            data = retry_response.json()
                            if data: return data
                    break # Stop if symbol is definitely wrong
                
                last_error = f"Status {response.status_code}: {response.text}"
                logger.warning(f"Binance endpoint {base_url} failed: {last_error}")
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Connect failed for {base_url}: {last_error}")
                continue

        # 2. Ultimate Fallback: KuCoin
        logger.info(f"Falling back to KuCoin for symbol: {symbol}")
        try:
            # KuCoin Interval Mapping
            kucoin_intervals = {"1m": "1min", "5m": "5min", "15m": "15min", "1h": "1hour", "4h": "4hour", "1d": "1day"}
            k_interval = kucoin_intervals.get(interval, "1hour")
            
            # Robust KuCoin symbol mapping
            clean_s = symbol.upper().replace("/", "").replace(" ", "")
            if "BTC" in clean_s: ku_symbol = "BTC-USDT"
            elif "ETH" in clean_s: ku_symbol = "ETH-USDT"
            elif "XAU" in clean_s or "PAXG" in clean_s: ku_symbol = "PAXG-USDT"
            elif "EUR" in clean_s: ku_symbol = "EUR-USDT"
            elif "GBP" in clean_s: ku_symbol = "GBP-USDT"
            else:
                base = clean_s.replace("USDT", "").replace("USD", "")
                ku_symbol = f"{base}-USDT"
            
            ku_params = {
                "symbol": ku_symbol,
                "type": k_interval,
                "startAt": int(start_time / 1000) if start_time else 0,
                "endAt": int(end_time / 1000) if end_time else int(datetime.now().timestamp())
            }
            
            logger.info(f"Calling KuCoin: {ku_symbol} | {k_interval}")
            response = requests.get(cls.KUCOIN_URL, params=ku_params, timeout=10)
            if response.status_code == 200:
                resp_json = response.json()
                data = resp_json.get("data", [])
                if data and len(data) > 0:
                    # KuCoin format: [time, open, close, high, low, volume, turnover]
                    # We need: [time*1000, open, high, low, close, volume]
                    return [[int(k[0])*1000, k[1], k[3], k[4], k[2], k[5]] for k in data[::-1]]
                else:
                    last_error = f"KuCoin empty: {resp_json.get('msg')}"
        except Exception as e:
            logger.error(f"KuCoin fallback failed: {str(e)}")
            last_error = f"KuCoin exception: {str(e)}"

        raise Exception(f"All market data services blocked or failed. Last error: {last_error}")

    @classmethod
    async def get_klines(
        cls, 
        symbol: str, 
        interval: str = "1h", 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None, 
        limit: int = 500
    ) -> List[List[Any]]:
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool, cls.get_klines_sync, 
                symbol, interval, start_time, end_time, limit
            )

binance_service = BinanceService()
