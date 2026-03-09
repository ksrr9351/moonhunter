"""
OHLCV Data Manager
Ingests price data from MarketProvider, builds candlestick data, manages historical storage
"""
import asyncio
import logging
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List, Tuple
from motor.motor_asyncio import AsyncIOMotorClient

logger = logging.getLogger(__name__)

OHLCV_TIMEFRAMES = {"5m": 300, "15m": 900, "1h": 3600}
MAX_CANDLES_PER_SYMBOL = 200


class DataManager:

    def __init__(self, db):
        self.db = db
        self.candles_collection = db.ohlcv_candles
        self.snapshots_collection = db.price_snapshots
        self._price_buffer: Dict[str, List[Dict]] = {}

    async def initialize(self):
        await self.candles_collection.create_index(
            [("symbol", 1), ("timeframe", 1), ("timestamp", -1)]
        )
        await self.candles_collection.create_index(
            [("timestamp", -1)]
        )
        await self.snapshots_collection.create_index(
            [("symbol", 1), ("timestamp", -1)]
        )
        logger.info("DataManager initialized with OHLCV indexes")

    async def ingest_market_data(self, coins: List[Dict]):
        now = datetime.now(timezone.utc)
        batch_ops = []

        for coin in coins:
            symbol = coin.get("symbol", "")
            price = coin.get("price", 0)
            volume = coin.get("volume24h", 0) or 0
            if not symbol or not price:
                continue

            snapshot = {
                "symbol": symbol,
                "price": price,
                "volume": volume,
                "market_cap": coin.get("marketCap", 0) or 0,
                "change1h": coin.get("change1h", 0) or 0,
                "change24h": coin.get("change24h", 0) or 0,
                "change7d": coin.get("change7d", 0) or 0,
                "name": coin.get("name", ""),
                "logo": coin.get("logo", ""),
                "timestamp": now.isoformat(),
            }
            batch_ops.append(snapshot)

            if symbol not in self._price_buffer:
                self._price_buffer[symbol] = []
            self._price_buffer[symbol].append({
                "price": price,
                "volume": volume,
                "timestamp": now,
            })
            if len(self._price_buffer[symbol]) > 500:
                self._price_buffer[symbol] = self._price_buffer[symbol][-500:]

        if batch_ops:
            try:
                await self.snapshots_collection.insert_many(batch_ops, ordered=False)
            except Exception as e:
                logger.error(f"Snapshot insert error: {e}")

        await self._build_candles_from_buffer()

    async def _build_candles_from_buffer(self):
        now = datetime.now(timezone.utc)

        for symbol, ticks in self._price_buffer.items():
            if len(ticks) < 2:
                continue

            for tf_name, tf_seconds in OHLCV_TIMEFRAMES.items():
                candle_start = now.replace(
                    second=0, microsecond=0,
                    minute=(now.minute // (tf_seconds // 60)) * (tf_seconds // 60)
                ) if tf_seconds < 3600 else now.replace(minute=0, second=0, microsecond=0)

                window_ticks = [t for t in ticks if t["timestamp"] >= candle_start]
                if not window_ticks:
                    continue

                prices = [t["price"] for t in window_ticks]
                volumes = [t["volume"] for t in window_ticks]

                candle = {
                    "symbol": symbol,
                    "timeframe": tf_name,
                    "timestamp": candle_start.isoformat(),
                    "open": prices[0],
                    "high": max(prices),
                    "low": min(prices),
                    "close": prices[-1],
                    "volume": sum(volumes),
                    "tick_count": len(window_ticks),
                    "updated_at": now.isoformat(),
                }

                try:
                    await self.candles_collection.update_one(
                        {"symbol": symbol, "timeframe": tf_name, "timestamp": candle_start.isoformat()},
                        {"$set": candle},
                        upsert=True,
                    )
                except Exception as e:
                    logger.error(f"Candle upsert error for {symbol}/{tf_name}: {e}")

    async def get_ohlcv(
        self, symbol: str, timeframe: str = "5m", limit: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        try:
            candles = await self.candles_collection.find(
                {"symbol": symbol, "timeframe": timeframe},
                sort=[("timestamp", -1)],
                limit=limit,
            ).to_list(limit)

            if not candles or len(candles) < 5:
                return await self._fallback_from_snapshots(symbol, limit)

            candles.reverse()
            opens = np.array([c["open"] for c in candles], dtype=float)
            highs = np.array([c["high"] for c in candles], dtype=float)
            lows = np.array([c["low"] for c in candles], dtype=float)
            closes = np.array([c["close"] for c in candles], dtype=float)
            volumes = np.array([c["volume"] for c in candles], dtype=float)
            return opens, highs, lows, closes, volumes

        except Exception as e:
            logger.error(f"OHLCV fetch error for {symbol}: {e}")
            return await self._fallback_from_snapshots(symbol, limit)

    async def _fallback_from_snapshots(
        self, symbol: str, limit: int = 100
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        try:
            snapshots = await self.snapshots_collection.find(
                {"symbol": symbol},
                sort=[("timestamp", -1)],
                limit=limit,
            ).to_list(limit)

            if not snapshots:
                return (np.array([]), np.array([]), np.array([]), np.array([]), np.array([]))

            snapshots.reverse()
            prices = np.array([s["price"] for s in snapshots], dtype=float)
            volumes = np.array([s.get("volume", 0) for s in snapshots], dtype=float)
            return prices, prices, prices, prices, volumes

        except Exception as e:
            logger.error(f"Snapshot fallback error for {symbol}: {e}")
            return (np.array([]), np.array([]), np.array([]), np.array([]), np.array([]))

    async def get_latest_snapshot(self, symbol: str) -> Optional[Dict]:
        try:
            return await self.snapshots_collection.find_one(
                {"symbol": symbol},
                sort=[("timestamp", -1)],
            )
        except Exception:
            return None

    async def cleanup_old_data(self, hours: int = 48):
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
        try:
            snap_result = await self.snapshots_collection.delete_many(
                {"timestamp": {"$lt": cutoff}}
            )
            candle_result = await self.candles_collection.delete_many(
                {"timestamp": {"$lt": cutoff}}
            )
            total = snap_result.deleted_count + candle_result.deleted_count
            if total > 0:
                logger.info(f"DataManager cleaned {total} old records")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

    async def get_tracked_symbols(self) -> List[str]:
        try:
            return await self.snapshots_collection.distinct("symbol")
        except Exception:
            return []

    async def get_data_stats(self) -> Dict[str, Any]:
        try:
            snap_count = await self.snapshots_collection.count_documents({})
            candle_count = await self.candles_collection.count_documents({})
            symbols = await self.snapshots_collection.distinct("symbol")
            return {
                "snapshots": snap_count,
                "candles": candle_count,
                "symbols_tracked": len(symbols),
                "buffer_symbols": len(self._price_buffer),
            }
        except Exception:
            return {"snapshots": 0, "candles": 0, "symbols_tracked": 0, "buffer_symbols": 0}
