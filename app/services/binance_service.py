import httpx
import logging
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
    async def get_klines(
        cls, 
        symbol: str, 
        interval: str = "1h", 
        start_time: Optional[int] = None, 
        end_time: Optional[int] = None, 
        limit: int = 500
    ) -> List[List[Any]]:
        """
        Fetch kline/candlestick data from Binance.
        
        Args:
            symbol: Symbol string (e.g., BTCUSDT)
            interval: Kline interval (e.g., 1m, 1h, 1d)
            start_time: Timestamp in ms
            end_time: Timestamp in ms
            limit: Number of results
            
        Returns:
            List of klines: [
                [
                    1499040000000,      // Open time
                    "0.01634790",       // Open
                    "0.80000000",       // High
                    "0.01575800",       // Low
                    "0.01577100",       // Close
                    "148976.11427815",  // Volume
                    1499644799999,      // Close time
                    "2434.19055334",    // Quote asset volume
                    308,                // Number of trades
                    "1756.87402397",    // Taker buy base asset volume
                    "28.46694368",      // Taker buy quote asset volume
                    "17928899.62484339" // Ignore
                ]
            ]
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
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{cls.BASE_URL}/api/v3/klines", params=params)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Binance API error: {e.response.text}")
            # If mapping failed, try common patterns
            if e.response.status_code == 400 and "Invalid symbol" in e.response.text:
                if "USD" in binance_symbol and "USDT" not in binance_symbol:
                    params["symbol"] = binance_symbol.replace("USD", "USDT")
                    async with httpx.AsyncClient() as client:
                        response = await client.get(f"{cls.BASE_URL}/api/v3/klines", params=params)
                        if response.status_code == 200:
                            return response.json()
            
            raise Exception(f"Failed to fetch data from Binance: {e.response.text}")
        except Exception as e:
            logger.error(f"Unexpected error fetching Binance data: {str(e)}")
            raise

binance_service = BinanceService()
