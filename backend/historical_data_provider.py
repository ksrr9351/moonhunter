"""
Historical Data Provider for Moon Hunters Backtesting
Uses CoinGecko API for free historical OHLC data
Set COINGECKO_API_KEY env var for a free demo key (get one at coingecko.com/api)
"""

import os
import httpx
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone, timedelta
import asyncio

logger = logging.getLogger("historical_data")

SYMBOL_TO_COINGECKO_ID = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "BNB": "binancecoin",
    "SOL": "solana",
    "XRP": "ripple",
    "DOGE": "dogecoin",
    "ADA": "cardano",
    "MATIC": "matic-network",
    "DOT": "polkadot",
    "AVAX": "avalanche-2",
    "LINK": "chainlink",
    "UNI": "uniswap",
    "ATOM": "cosmos",
    "NEAR": "near",
    "FTM": "fantom",
    "LTC": "litecoin",
    "SHIB": "shiba-inu",
    "TRX": "tron",
    "ETC": "ethereum-classic",
    "XLM": "stellar",
    "APT": "aptos",
    "ARB": "arbitrum",
    "OP": "optimism",
    "INJ": "injective-protocol",
    "FIL": "filecoin",
    "HBAR": "hedera-hashgraph",
    "VET": "vechain",
    "ICP": "internet-computer",
    "IMX": "immutable-x",
    "ALGO": "algorand",
    "AAVE": "aave",
    "MKR": "maker",
    "GRT": "the-graph",
    "SAND": "the-sandbox",
    "MANA": "decentraland",
    "AXS": "axie-infinity",
    "THETA": "theta-token",
    "FTT": "ftx-token",
    "CRO": "crypto-com-chain",
    "LEO": "leo-token",
}


class HistoricalDataProvider:
    """Provider for real historical OHLC data from CoinGecko"""
    
    def __init__(self):
        self.base_url = "https://api.coingecko.com/api/v3"
        self.api_key = os.environ.get('COINGECKO_API_KEY', '')
        self.cache: Dict[str, Any] = {}
        self.cache_ttl = 7200  # Cache for 2 hours to reduce API calls
        # With API key: 30 req/min → ~2s safe delay. Without: be more conservative
        self.rate_limit_delay = 2.0 if self.api_key else 3.0
        self.last_request_time = 0
        self.retry_count = 0
        self.max_retries = 3
        if self.api_key:
            logger.info("Historical Data Provider initialized (CoinGecko with API key)")
        else:
            logger.warning(
                "Historical Data Provider initialized WITHOUT CoinGecko API key. "
                "Set COINGECKO_API_KEY env var for reliable data. "
                "Get a free key at https://www.coingecko.com/en/api"
            )
    
    def _get_coingecko_id(self, symbol: str) -> Optional[str]:
        """Convert CMC symbol to CoinGecko ID"""
        return SYMBOL_TO_COINGECKO_ID.get(symbol.upper())
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached data is still valid"""
        if cache_key not in self.cache:
            return False
        entry = self.cache[cache_key]
        age = (datetime.now(timezone.utc) - entry["timestamp"]).total_seconds()
        return age < self.cache_ttl
    
    async def _rate_limit(self):
        """Ensure we don't exceed CoinGecko rate limits (30/min free tier)"""
        now = asyncio.get_event_loop().time()
        elapsed = now - self.last_request_time
        if elapsed < self.rate_limit_delay:
            await asyncio.sleep(self.rate_limit_delay - elapsed)
        self.last_request_time = asyncio.get_event_loop().time()
    
    async def get_historical_ohlc(
        self,
        symbol: str,
        days: int = 90
    ) -> List[Dict[str, Any]]:
        """
        Fetch real historical OHLC data from CoinGecko
        
        Args:
            symbol: Cryptocurrency symbol (e.g., 'BTC', 'ETH')
            days: Number of days of history (max 365 for free tier)
        
        Returns:
            List of OHLC candles with timestamp, open, high, low, close
        """
        coin_id = self._get_coingecko_id(symbol)
        if not coin_id:
            logger.warning(f"No CoinGecko ID mapping for {symbol}")
            return []
        
        cache_key = f"ohlc_{coin_id}_{days}"
        if self._is_cache_valid(cache_key):
            logger.debug(f"Cache hit for {symbol} historical data")
            return self.cache[cache_key]["data"]
        
        days = min(days, 365)
        
        valid_days = [1, 7, 14, 30, 90, 180, 365]
        api_days = min([d for d in valid_days if d >= days], default=365)
        
        await self._rate_limit()
        
        # Build request headers — include API key when available
        headers = {}
        if self.api_key:
            headers["x-cg-demo-api-key"] = self.api_key

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/coins/{coin_id}/ohlc",
                    params={
                        "vs_currency": "usd",
                        "days": str(api_days)
                    },
                    headers=headers
                )
                
                if response.status_code == 429:
                    self.retry_count += 1
                    if self.retry_count > self.max_retries:
                        logger.error(f"CoinGecko rate limit exceeded after {self.max_retries} retries for {symbol}")
                        self.retry_count = 0
                        return []
                    wait_time = 30 * self.retry_count  # Exponential backoff: 30s, 60s, 90s
                    logger.warning(f"CoinGecko rate limit hit, waiting {wait_time}s (retry {self.retry_count}/{self.max_retries})...")
                    await asyncio.sleep(wait_time)
                    return await self.get_historical_ohlc(symbol, days)

                if response.status_code in (401, 403):
                    logger.error(
                        f"CoinGecko auth error {response.status_code} for {symbol}. "
                        f"Set COINGECKO_API_KEY env var with your free demo key "
                        f"(get one at https://www.coingecko.com/en/api). "
                        f"Falling back to /market_chart endpoint..."
                    )
                    return await self._get_ohlc_from_market_chart(coin_id, symbol, api_days, headers)
                
                response.raise_for_status()
                raw_data = response.json()
                
                candles = []
                for item in raw_data:
                    if len(item) >= 5:
                        candles.append({
                            "timestamp": item[0],
                            "date": datetime.fromtimestamp(item[0] / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                            "open": float(item[1]),
                            "high": float(item[2]),
                            "low": float(item[3]),
                            "close": float(item[4])
                        })

                if not candles:
                    logger.warning(f"OHLC returned empty data for {symbol}, falling back to market_chart...")
                    return await self._get_ohlc_from_market_chart(coin_id, symbol, api_days, headers)
                
                self.cache[cache_key] = {
                    "data": candles,
                    "timestamp": datetime.now(timezone.utc)
                }
                
                logger.info(f"Fetched {len(candles)} OHLC candles for {symbol}")
                return candles
                
        except httpx.HTTPStatusError as e:
            logger.error(f"CoinGecko API error for {symbol}: {e}")
            return await self._get_ohlc_from_market_chart(coin_id, symbol, api_days, headers)
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {e}")
            return []

    async def _get_ohlc_from_market_chart(
        self,
        coin_id: str,
        symbol: str,
        days: int,
        headers: Dict[str, str]
    ) -> List[Dict[str, Any]]:
        """
        Fallback: build synthetic OHLC candles from /coins/{id}/market_chart
        which returns daily close prices and is more permissive on free tier.
        """
        cache_key = f"market_chart_{coin_id}_{days}"
        if self._is_cache_valid(cache_key):
            return self.cache[cache_key]["data"]

        await self._rate_limit()
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.base_url}/coins/{coin_id}/market_chart",
                    params={"vs_currency": "usd", "days": str(days), "interval": "daily"},
                    headers=headers
                )
                if response.status_code == 429:
                    logger.warning(f"Rate limit on market_chart for {symbol}, skipping")
                    return []
                if response.status_code in (401, 403):
                    logger.error(
                        f"CoinGecko {response.status_code} on market_chart for {symbol}. "
                        f"Please set COINGECKO_API_KEY. Get a FREE key at https://www.coingecko.com/en/api"
                    )
                    return []
                response.raise_for_status()
                data = response.json()
                prices = data.get("prices", [])  # [[ts_ms, price], ...]
                if not prices:
                    return []

                candles = []
                for i, (ts, price) in enumerate(prices):
                    open_price = prices[i - 1][1] if i > 0 else price
                    candles.append({
                        "timestamp": ts,
                        "date": datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%d"),
                        "open": float(open_price),
                        "high": float(max(open_price, price)),
                        "low": float(min(open_price, price)),
                        "close": float(price)
                    })

                self.cache[cache_key] = {
                    "data": candles,
                    "timestamp": datetime.now(timezone.utc)
                }
                logger.info(f"Fetched {len(candles)} market_chart candles (fallback) for {symbol}")
                return candles
        except Exception as e:
            logger.error(f"market_chart fallback also failed for {symbol}: {e}")
            return []
    
    async def get_daily_prices(
        self,
        symbol: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict[str, float]:
        """
        Get daily closing prices for a date range
        
        Returns:
            Dict mapping date string (YYYY-MM-DD) to closing price
        """
        days = (end_date - start_date).days + 30
        candles = await self.get_historical_ohlc(symbol, days)
        
        if not candles:
            return {}
        
        prices = {}
        start_str = start_date.strftime("%Y-%m-%d")
        end_str = end_date.strftime("%Y-%m-%d")
        
        for candle in candles:
            date_str = candle["date"]
            if start_str <= date_str <= end_str:
                prices[date_str] = candle["close"]
        
        return prices
    
    async def get_price_at_date(
        self,
        symbol: str,
        target_date: datetime
    ) -> Optional[float]:
        """Get closing price for a specific date"""
        prices = await self.get_daily_prices(
            symbol,
            target_date - timedelta(days=7),
            target_date + timedelta(days=1)
        )
        
        target_str = target_date.strftime("%Y-%m-%d")
        if target_str in prices:
            return prices[target_str]
        
        for date_str in sorted(prices.keys(), reverse=True):
            if date_str <= target_str:
                return prices[date_str]
        
        return list(prices.values())[0] if prices else None
    
    async def get_multiple_coins_history(
        self,
        symbols: List[str],
        days: int = 90
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Fetch historical data for multiple coins
        Uses sequential requests with rate limiting
        """
        results = {}
        
        for symbol in symbols:
            data = await self.get_historical_ohlc(symbol, days)
            if data:
                results[symbol] = data
        
        return results
    
    def get_supported_symbols(self) -> List[str]:
        """Get list of supported cryptocurrency symbols"""
        return list(SYMBOL_TO_COINGECKO_ID.keys())


historical_data_provider: Optional[HistoricalDataProvider] = None


def init_historical_data_provider() -> HistoricalDataProvider:
    """Initialize the historical data provider singleton"""
    global historical_data_provider
    historical_data_provider = HistoricalDataProvider()
    return historical_data_provider


def get_historical_data_provider() -> Optional[HistoricalDataProvider]:
    """Get the historical data provider instance"""
    return historical_data_provider
