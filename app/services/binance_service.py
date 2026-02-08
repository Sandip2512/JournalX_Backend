import logging
import requests
from datetime import datetime
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)

class BinanceService:
    BASE_URL = "https://api.binance.com"
    
    # Mapping for common symbols to Binance symbols
    SYMBOL_MAPPING = {
        "XAU/USD": "PAXGUSDT",
        "BTC/USD": "BTCUSDT",
        "ETH/USD": "ETHUSDT",
        "GBP/USD": "GBPUSDT",
        "EUR/USD": "EURUSDT",
        "JPY/USD": "JPYUSDT", # Binance uses USDJPY usually
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
        Synchronous kline fetch using requests.
        """
        # Try to map symbol if needed
        binance_symbol = cls.SYMBOL_MAPPING.get(symbol, symbol.replace("/", "").replace(" ", ""))
        
        params = {
            "symbol": binance_symbol,
            "interval": interval,
            "limit": limit
        }
        
        if start_time:
            params["startTime"] = start_time
        if end_time:
            params["endTime"] = end_time

        try:
            response = requests.get(f"{cls.BASE_URL}/api/v3/klines", params=params, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Binance API error: {str(e)}")
            # If mapping failed, try common patterns
            if response.status_code == 400 and "Invalid symbol" in response.text:
                if "USD" in binance_symbol and "USDT" not in binance_symbol:
                    params["symbol"] = binance_symbol.replace("USD", "USDT")
                    retry_response = requests.get(f"{cls.BASE_URL}/api/v3/klines", params=params, timeout=10)
                    if retry_response.status_code == 200:
                        return retry_response.json()
            
            raise Exception(f"Failed to fetch data from Binance: {str(e)}")

    @classmethod
    async def get_klines(
        cls, 
        symbol: str, 
        interval: str = "1h", 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None, 
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Async wrapper for the sync method.
        """
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as pool:
            return await loop.run_in_executor(
                pool, 
                cls.get_klines_sync, 
                symbol, interval, start_time, end_time, limit
            )

binance_service = BinanceService()
