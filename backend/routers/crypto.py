from fastapi import APIRouter, Request, Query, HTTPException
from datetime import datetime, timezone
import hashlib
import logging

from core.deps import market_provider, fast_movers_detector, limiter, db
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/crypto/latest")
@limiter.limit("60/minute")
async def get_crypto_latest(request: Request, limit: int = Query(10, ge=1, le=100)):
    """Get latest cryptocurrency listings from CoinMarketCap Pro API"""
    try:
        logger.info(f"Fetching {limit} coins from CoinMarketCap...")
        coins = await market_provider.get_coins_list(limit)
        
        for i, coin in enumerate(coins):
            try:
                symbol = coin["symbol"]
                history = await market_provider.get_coin_history(symbol, days=7)
                coin["sparkline"] = history
            except Exception as e:
                logger.warning(f"Error fetching history for {coin['symbol']}: {e}")
                symbol = coin["symbol"]
                base = 100
                change7d = coin.get("change7d", 0)
                seed = int(hashlib.md5(symbol.encode()).hexdigest()[:8], 16) % 1000
                sparkline = []
                current = base
                for day in range(7):
                    trend = (change7d / 100) * (day / 6)
                    volatility = ((seed + day * 13) % 20 - 10) * 0.3
                    current = base * (1 + trend + (volatility / 100))
                    sparkline.append(round(current, 2))
                coin["sparkline"] = sparkline
        
        return {
            "data": coins,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching crypto data: {e}", exc_info=True)
        stale = market_provider._get_stale_data("coins_list_100")
        if stale:
            logger.info("Returning stale crypto data to client after API error")
            return {
                "data": stale[:limit],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stale": True
            }
        raise HTTPException(status_code=503, detail="External API error")
    except Exception as e:
        logger.error(f"Error in /crypto/latest: {str(e)}", exc_info=True)
        stale = market_provider._get_stale_data("coins_list_100")
        if stale:
            return {
                "data": stale[:limit],
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "stale": True
            }
        raise HTTPException(status_code=503, detail="Failed to fetch crypto data")


@router.get("/crypto/market-overview")
@limiter.limit("60/minute")
async def get_market_overview(request: Request):
    """Get market overview with top gainers, losers, trending tokens, and global stats"""
    try:
        overview = await market_provider.get_market_overview()
        return overview
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error fetching market overview: {e}", exc_info=True)
        stale = market_provider._get_stale_data("market_overview")
        if stale:
            logger.info("Returning stale market overview to client after API error")
            stale["stale"] = True
            return stale
        raise HTTPException(status_code=503, detail="External API error")
    except Exception as e:
        logger.error(f"Error in /crypto/market-overview: {str(e)}", exc_info=True)
        stale = market_provider._get_stale_data("market_overview")
        if stale:
            stale["stale"] = True
            return stale
        raise HTTPException(status_code=503, detail="Failed to fetch market overview")


@router.get("/crypto/market-health")
@limiter.limit("60/minute")
async def get_market_health(request: Request):
    """Get market health score based on cap and volume changes"""
    try:
        health = await market_provider.get_market_health_score()
        return health
    except Exception as e:
        logger.error(f"Error in /crypto/market-health: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail="Failed to fetch market health")


@router.get("/crypto/fast-movers")
@limiter.limit("60/minute")
async def get_fast_movers(request: Request):
    """Get fast moving cryptocurrencies with significant price changes, merged with centralized dump opportunities"""
    try:
        fast_movers = await fast_movers_detector.get_recent_movers()

        now = datetime.utcnow()
        dump_opps = await db.dump_opportunities.find(
            {"expires_at": {"$gt": now}}, {"_id": 0}
        ).to_list(50)

        fm_by_symbol = {m.get("symbol"): i for i, m in enumerate(fast_movers)}

        for opp in dump_opps:
            symbol = opp.get("symbol", "")
            detected_at = opp.get("detected_at")
            if isinstance(detected_at, datetime):
                ts = detected_at.isoformat()
            elif isinstance(detected_at, str):
                ts = detected_at
            else:
                ts = now.isoformat()

            dump_entry = {
                "symbol": symbol,
                "name": opp.get("name", symbol),
                "price": opp.get("current_price", 0),
                "current_price": opp.get("current_price", 0),
                "previous_price": 0,
                "price_change_percent": round(opp.get("dump_percentage", 0), 2),
                "change_24h": round(opp.get("change_24h", 0), 2),
                "movement_type": "dump",
                "timestamp": ts,
                "volume_24h": opp.get("volume_24h", 0),
                "market_cap": opp.get("market_cap", 0),
                "logo": opp.get("logo", "")
            }

            if symbol in fm_by_symbol:
                fast_movers[fm_by_symbol[symbol]] = dump_entry
            else:
                fast_movers.append(dump_entry)

        return fast_movers
    except Exception as e:
        logger.error(f"Error in /crypto/fast-movers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail="Failed to fetch fast movers")


@router.get("/crypto/ohlc/{symbol}")
@limiter.limit("60/minute")
async def get_ohlc_data(
    request: Request,
    symbol: str,
    interval: str = "1d",
    limit: int = 100
):
    """
    Get OHLC candlestick data for TradingView-style charts.
    Intervals: 1h, 4h, 1d, 1w
    """
    try:
        if interval not in ["1h", "4h", "1d", "1w"]:
            raise HTTPException(status_code=400, detail="Invalid interval. Use: 1h, 4h, 1d, 1w")
        
        if limit < 10 or limit > 500:
            limit = min(max(limit, 10), 500)
        
        candles = await market_provider.get_ohlc_data(symbol.upper(), interval, limit)
        
        if not candles:
            raise HTTPException(status_code=404, detail=f"Coin {symbol} not found")
        
        return {
            "symbol": symbol.upper(),
            "interval": interval,
            "count": len(candles),
            "data": candles
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching OHLC data for {symbol}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=503, detail="Failed to fetch OHLC data")
