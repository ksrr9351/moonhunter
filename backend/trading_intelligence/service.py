"""
Trading Intelligence Service - Main Orchestrator
Combines all modules into a unified API for signal generation and market analysis
"""
import asyncio
import logging
import time
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, List


def _sanitize(obj):
    """Recursively convert numpy types to native Python types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _sanitize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_sanitize(v) for v in obj]
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    return obj

from trading_intelligence.indicators import compute_all_indicators
from trading_intelligence.anomaly_detector import anomaly_detector
from trading_intelligence.pump_dump_detector import pump_dump_detector
from trading_intelligence.signal_engine import signal_engine
from trading_intelligence.data_manager import DataManager

logger = logging.getLogger(__name__)


class TradingIntelligenceService:

    SIGNAL_CACHE_TTL = 30
    TOP_COINS_LIMIT = 50
    BACKGROUND_INTERVAL = 60

    def __init__(self, db, market_provider):
        self.db = db
        self.market_provider = market_provider
        self.data_manager = DataManager(db)
        self._signal_cache: Dict[str, Dict] = {}
        self._cache_timestamps: Dict[str, float] = {}
        self._all_signals_cache: List[Dict] = []
        self._all_signals_timestamp: float = 0
        self._running = False
        self._initialized = False

    async def initialize(self):
        try:
            await self.data_manager.initialize()
            signal_engine.seed_model()
            self._initialized = True
            logger.info("Trading Intelligence Service initialized")
        except Exception as e:
            logger.error(f"TI Service init error: {e}")
            self._initialized = False

    async def get_signal(self, symbol: str) -> Dict[str, Any]:
        now = time.time()
        cached = self._signal_cache.get(symbol)
        cache_ts = self._cache_timestamps.get(symbol, 0)
        if cached and (now - cache_ts) < self.SIGNAL_CACHE_TTL:
            return cached

        try:
            opens, highs, lows, closes, volumes = await self.data_manager.get_ohlcv(
                symbol, timeframe="5m", limit=100
            )

            if len(closes) < 5:
                return self._empty_signal(symbol, "Insufficient price data")

            snapshot = await self.data_manager.get_latest_snapshot(symbol)
            change_1h = snapshot.get("change1h", 0) if snapshot else 0
            change_24h = snapshot.get("change24h", 0) if snapshot else 0
            change_7d = snapshot.get("change7d", 0) if snapshot else 0
            market_cap = snapshot.get("market_cap", 0) if snapshot else 0
            volume_24h = snapshot.get("volume", 0) if snapshot else 0
            coin_name = snapshot.get("name", symbol) if snapshot else symbol
            coin_price = snapshot.get("price", float(closes[-1])) if snapshot else float(closes[-1])
            logo = snapshot.get("logo", "") if snapshot else ""

            indicators = compute_all_indicators(closes, highs, lows, volumes)

            anomaly = anomaly_detector.detect(closes, volumes, symbol)

            pd_result = pump_dump_detector.analyze(
                closes, volumes, highs, lows, change_1h, change_24h
            )

            signal_result = signal_engine.generate_signal(
                indicators=indicators,
                anomaly=anomaly,
                pump_dump=pd_result,
                change_1h=change_1h,
                change_24h=change_24h,
                change_7d=change_7d,
                market_cap=market_cap,
                volume_24h=volume_24h,
            )

            output = {
                "symbol": symbol,
                "name": coin_name,
                "price": coin_price,
                "logo": logo,
                "signal": signal_result["signal"],
                "confidence": signal_result["confidence"],
                "pump_dump_risk": pd_result["risk_percentage"],
                "movement_strength": signal_result["movement_strength"],
                "volume_anomaly": anomaly["volume_anomaly"],
                "timestamp": int(time.time()),
                "indicators": {
                    "rsi": indicators.get("rsi"),
                    "macd": indicators.get("macd"),
                    "macd_signal": indicators.get("macd_signal"),
                    "macd_histogram": indicators.get("macd_histogram"),
                    "vwap": indicators.get("vwap"),
                    "bollinger_upper": indicators.get("bollinger_upper"),
                    "bollinger_middle": indicators.get("bollinger_middle"),
                    "bollinger_lower": indicators.get("bollinger_lower"),
                    "momentum": indicators.get("momentum"),
                    "volume_delta": indicators.get("volume_delta"),
                    "volume_sma_ratio": indicators.get("volume_sma_ratio"),
                    "atr": indicators.get("atr"),
                    "obv_trend": indicators.get("obv_trend"),
                    "price_vs_vwap": indicators.get("price_vs_vwap"),
                },
                "anomaly": {
                    "is_anomaly": anomaly["is_anomaly"],
                    "anomaly_score": anomaly["anomaly_score"],
                    "volume_zscore": anomaly["volume_zscore"],
                    "price_zscore": anomaly["price_zscore"],
                    "isolation_score": anomaly["isolation_score"],
                },
                "pump_dump": {
                    "is_pump": pd_result["is_pump"],
                    "is_dump": pd_result["is_dump"],
                    "pattern_type": pd_result["pattern_type"],
                    "volume_surge_ratio": pd_result["volume_surge_ratio"],
                    "price_velocity": pd_result["price_velocity"],
                    "reversal_probability": pd_result["reversal_probability"],
                    "reasons": pd_result["reasons"],
                },
                "reasons": signal_result["reasons"],
                "risk_level": signal_result["risk_level"],
                "change_1h": change_1h,
                "change_24h": change_24h,
                "change_7d": change_7d,
                "market_cap": market_cap,
                "volume_24h": volume_24h,
                "data_points": len(closes),
            }

            output = _sanitize(output)
            self._signal_cache[symbol] = output
            self._cache_timestamps[symbol] = now
            return output

        except Exception as e:
            logger.error(f"Signal generation error for {symbol}: {e}")
            return self._empty_signal(symbol, str(e))

    def _evict_stale_cache(self):
        now = time.time()
        max_age = 3600
        stale_keys = [k for k, ts in self._cache_timestamps.items() if (now - ts) > max_age]
        for key in stale_keys:
            self._signal_cache.pop(key, None)
            self._cache_timestamps.pop(key, None)
        if stale_keys:
            logger.debug(f"Evicted {len(stale_keys)} stale cache entries")

    async def get_all_signals(self, limit: int = 50) -> List[Dict[str, Any]]:
        now = time.time()
        self._evict_stale_cache()
        if self._all_signals_cache and (now - self._all_signals_timestamp) < self.SIGNAL_CACHE_TTL:
            return self._all_signals_cache[:limit]

        try:
            coins = await self.market_provider.get_coins_list(limit=limit)
            if not coins:
                return []

            await self.data_manager.ingest_market_data(coins)

            tasks = [self.get_signal(coin["symbol"]) for coin in coins[:limit]]
            signals = await asyncio.gather(*tasks, return_exceptions=True)

            results = []
            for sig in signals:
                if isinstance(sig, Exception):
                    logger.error(f"Signal task error: {sig}")
                    continue
                if sig and sig.get("signal"):
                    results.append(sig)

            results.sort(key=lambda x: x.get("confidence", 0), reverse=True)

            self._all_signals_cache = results
            self._all_signals_timestamp = now
            return results[:limit]

        except Exception as e:
            logger.error(f"Batch signal error: {e}")
            return self._all_signals_cache[:limit] if self._all_signals_cache else []

    async def get_top_signals(self, signal_type: str = "BUY", limit: int = 10) -> List[Dict[str, Any]]:
        all_signals = await self.get_all_signals(limit=self.TOP_COINS_LIMIT)
        filtered = [s for s in all_signals if s.get("signal") == signal_type.upper()]
        filtered.sort(key=lambda x: x.get("confidence", 0), reverse=True)
        return filtered[:limit]

    async def get_anomalies(self, limit: int = 10) -> List[Dict[str, Any]]:
        all_signals = await self.get_all_signals(limit=self.TOP_COINS_LIMIT)
        anomalies = [s for s in all_signals if s.get("anomaly", {}).get("is_anomaly")]
        anomalies.sort(key=lambda x: x.get("anomaly", {}).get("anomaly_score", 0), reverse=True)
        return anomalies[:limit]

    async def get_pump_dump_alerts(self, limit: int = 10) -> List[Dict[str, Any]]:
        all_signals = await self.get_all_signals(limit=self.TOP_COINS_LIMIT)
        alerts = [s for s in all_signals if s.get("pump_dump_risk", 0) > 30]
        alerts.sort(key=lambda x: x.get("pump_dump_risk", 0), reverse=True)
        return alerts[:limit]

    async def pre_warm_models(self):
        try:
            symbols = await self.data_manager.get_tracked_symbols()
            if not symbols:
                return

            symbol_data = {}
            for symbol in symbols:
                _, _, _, closes, volumes = await self.data_manager.get_ohlcv(
                    symbol, timeframe="5m", limit=100
                )
                if len(closes) >= anomaly_detector.MIN_SAMPLES_FOR_ML:
                    symbol_data[symbol] = {"closes": closes, "volumes": volumes}

            if symbol_data:
                anomaly_detector.pre_warm_batch(symbol_data)
            elif symbols:
                logger.info(f"Pre-warm skipped: no symbols with enough data (need {anomaly_detector.MIN_SAMPLES_FOR_ML}+ samples)")
        except Exception as e:
            logger.error(f"Model pre-warming error: {e}")

    async def get_engine_stats(self) -> Dict[str, Any]:
        data_stats = await self.data_manager.get_data_stats()
        return {
            "initialized": self._initialized,
            "running": self._running,
            "cached_signals": len(self._signal_cache),
            "data": data_stats,
            "anomaly_models_loaded": len(anomaly_detector.models),
            "signal_ml_trained": signal_engine.model_trained,
            "last_batch_update": datetime.fromtimestamp(
                self._all_signals_timestamp, tz=timezone.utc
            ).isoformat() if self._all_signals_timestamp else None,
        }

    def _empty_signal(self, symbol: str, reason: str = "") -> Dict[str, Any]:
        return {
            "symbol": symbol,
            "signal": "HOLD",
            "confidence": 0.0,
            "pump_dump_risk": 0.0,
            "movement_strength": 0.0,
            "volume_anomaly": False,
            "timestamp": int(time.time()),
            "indicators": {},
            "anomaly": {},
            "pump_dump": {},
            "reasons": [reason] if reason else ["Insufficient data"],
            "risk_level": "unknown",
            "data_points": 0,
        }


ti_service: Optional[TradingIntelligenceService] = None


def init_trading_intelligence(db, market_provider) -> TradingIntelligenceService:
    global ti_service
    ti_service = TradingIntelligenceService(db, market_provider)
    logger.info("Trading Intelligence Service created")
    return ti_service


async def run_intelligence_background_task(service: TradingIntelligenceService):
    logger.info("Trading Intelligence background task starting...")

    for attempt in range(3):
        try:
            await service.initialize()
            break
        except Exception as e:
            logger.warning(f"TI init attempt {attempt + 1}/3 failed: {e}")
            await asyncio.sleep(5)
    else:
        logger.error("Trading Intelligence failed to initialize. Background task disabled.")
        return

    service._running = True
    cycle = 0

    await asyncio.sleep(5)

    while True:
        try:
            cycle += 1

            try:
                coins = await service.market_provider.get_coins_list(limit=service.TOP_COINS_LIMIT)
            except Exception as api_err:
                logger.debug(f"TI data fetch deferred (cache miss): {str(api_err)[:80]}")
                coins = None

            if coins:
                await service.data_manager.ingest_market_data(coins)

            if cycle % 5 == 1:
                await service.pre_warm_models()

            if cycle % 2 == 0 and coins:
                await service.get_all_signals(limit=service.TOP_COINS_LIMIT)

            if cycle % 120 == 0:
                await service.data_manager.cleanup_old_data(hours=48)

            await asyncio.sleep(service.BACKGROUND_INTERVAL)

        except Exception as e:
            logger.error(f"TI background task error: {e}")
            await asyncio.sleep(service.BACKGROUND_INTERVAL)
