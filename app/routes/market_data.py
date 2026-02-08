from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from app.services.binance_service import binance_service
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/klines")
async def get_klines(
    symbol: str,
    interval: str = "1h",
    start_time: Optional[int] = Query(None),
    end_time: Optional[int] = Query(None),
    limit: int = 500
):
    """
    Get kline data for a symbol from Binance.
    """
    try:
        logger.info(f"Market request: {symbol} | {interval} | {start_time}-{end_time}")
        data = await binance_service.get_klines(
            symbol=symbol,
            interval=interval,
            start_time=start_time,
            end_time=end_time,
            limit=limit
        )
        
        logger.info(f"Service returned {len(data)} items")
        if not data:
            logger.warning(f"Empty data from pool for {symbol}")
            
        # Transform Binance klines into a more chart-friendly format
        transformed_data = []
        for k in data:
            if not isinstance(k, list) or len(k) < 6: continue
            transformed_data.append({
                "time": k[0] / 1000, # Convert to seconds for lightweight-charts
                "open": float(k[1]),
                "high": float(k[2]),
                "low": float(k[3]),
                "close": float(k[4]),
                "volume": float(k[5])
            })
            
        return transformed_data
    except Exception as e:
        logger.error(f"Error in get_klines route: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
