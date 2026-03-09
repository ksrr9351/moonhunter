"""
Technical Indicators Engine
High-performance NumPy-based computation of RSI, MACD, VWAP, Bollinger, momentum, volume delta
"""
import numpy as np
import logging
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def compute_ema(data: np.ndarray, period: int) -> np.ndarray:
    if len(data) < period:
        return np.full_like(data, np.nan, dtype=float)
    alpha = 2.0 / (period + 1)
    ema = np.empty_like(data, dtype=float)
    ema[:period - 1] = np.nan
    ema[period - 1] = np.mean(data[:period])
    for i in range(period, len(data)):
        ema[i] = alpha * data[i] + (1 - alpha) * ema[i - 1]
    return ema


def compute_sma(data: np.ndarray, period: int) -> np.ndarray:
    if len(data) < period:
        return np.full_like(data, np.nan, dtype=float)
    result = np.full_like(data, np.nan, dtype=float)
    cumsum = np.cumsum(data)
    result[period - 1:] = (cumsum[period - 1:] - np.concatenate([[0], cumsum[:-period]])) / period
    return result


def compute_rsi(closes: np.ndarray, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    deltas = np.diff(closes)
    gains = np.where(deltas > 0, deltas, 0.0)
    losses = np.where(deltas < 0, -deltas, 0.0)

    avg_gain = np.mean(gains[:period])
    avg_loss = np.mean(losses[:period])

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def compute_macd(closes: np.ndarray, fast: int = 12, slow: int = 26, signal_period: int = 9) -> Dict[str, Optional[float]]:
    if len(closes) < slow + signal_period:
        return {"macd": None, "signal": None, "histogram": None}

    ema_fast = compute_ema(closes, fast)
    ema_slow = compute_ema(closes, slow)
    macd_line = ema_fast - ema_slow

    valid_macd = macd_line[~np.isnan(macd_line)]
    if len(valid_macd) < signal_period:
        return {"macd": None, "signal": None, "histogram": None}

    signal_line = compute_ema(valid_macd, signal_period)

    macd_val = round(float(valid_macd[-1]), 6)
    signal_val = round(float(signal_line[-1]), 6) if not np.isnan(signal_line[-1]) else None
    histogram = round(macd_val - signal_val, 6) if signal_val is not None else None

    return {"macd": macd_val, "signal": signal_val, "histogram": histogram}


def compute_vwap(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, volumes: np.ndarray) -> Optional[float]:
    if len(closes) < 2 or np.sum(volumes) == 0:
        return None
    typical_price = (highs + lows + closes) / 3.0
    cumulative_tpv = np.cumsum(typical_price * volumes)
    cumulative_vol = np.cumsum(volumes)
    mask = cumulative_vol > 0
    if not mask.any():
        return None
    vwap_values = np.where(mask, cumulative_tpv / cumulative_vol, np.nan)
    return round(float(vwap_values[-1]), 6)


def compute_bollinger_bands(closes: np.ndarray, period: int = 20, std_dev: float = 2.0) -> Dict[str, Optional[float]]:
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None}
    sma = np.mean(closes[-period:])
    std = np.std(closes[-period:])
    return {
        "upper": round(sma + std_dev * std, 6),
        "middle": round(sma, 6),
        "lower": round(sma - std_dev * std, 6),
    }


def compute_momentum(closes: np.ndarray, period: int = 10) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    if closes[-period - 1] == 0:
        return None
    return round(((closes[-1] - closes[-period - 1]) / closes[-period - 1]) * 100, 4)


def compute_volume_delta(volumes: np.ndarray, closes: np.ndarray) -> Dict[str, Optional[float]]:
    if len(volumes) < 2 or len(closes) < 2:
        return {"delta": None, "sma_ratio": None}
    price_changes = np.diff(closes)
    vol_slice = volumes[1:]
    buy_volume = np.sum(vol_slice[price_changes > 0])
    sell_volume = np.sum(vol_slice[price_changes < 0])
    total = buy_volume + sell_volume
    delta = ((buy_volume - sell_volume) / total * 100) if total > 0 else 0.0

    vol_sma = np.mean(volumes[-20:]) if len(volumes) >= 20 else np.mean(volumes)
    sma_ratio = float(volumes[-1] / vol_sma) if vol_sma > 0 else 1.0

    return {"delta": round(delta, 2), "sma_ratio": round(sma_ratio, 4)}


def compute_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 14) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    tr = np.maximum(
        highs[1:] - lows[1:],
        np.maximum(
            np.abs(highs[1:] - closes[:-1]),
            np.abs(lows[1:] - closes[:-1])
        )
    )
    if len(tr) < period:
        return None
    atr = np.mean(tr[-period:])
    return round(float(atr), 6)


def compute_obv_trend(closes: np.ndarray, volumes: np.ndarray, period: int = 10) -> Optional[float]:
    if len(closes) < period + 1:
        return None
    direction = np.sign(np.diff(closes))
    obv_changes = direction * volumes[1:]
    obv = np.cumsum(obv_changes)
    if len(obv) < period:
        return None
    obv_recent = obv[-period:]
    if len(obv_recent) < 2:
        return None
    x = np.arange(len(obv_recent))
    slope = np.polyfit(x, obv_recent, 1)[0]
    normalized = slope / (np.mean(np.abs(obv_recent)) + 1e-10)
    return round(float(normalized), 6)


def compute_all_indicators(
    closes: np.ndarray,
    highs: np.ndarray,
    lows: np.ndarray,
    volumes: np.ndarray,
) -> Dict[str, Any]:
    rsi = compute_rsi(closes)
    macd_data = compute_macd(closes)
    vwap = compute_vwap(highs, lows, closes, volumes)
    bollinger = compute_bollinger_bands(closes)
    momentum = compute_momentum(closes)
    vol_delta = compute_volume_delta(volumes, closes)
    atr = compute_atr(highs, lows, closes)
    obv = compute_obv_trend(closes, volumes)

    current_price = float(closes[-1]) if len(closes) > 0 else 0
    price_vs_vwap = None
    if vwap and vwap > 0 and current_price > 0:
        price_vs_vwap = round(((current_price - vwap) / vwap) * 100, 4)

    return {
        "rsi": rsi,
        "macd": macd_data["macd"],
        "macd_signal": macd_data["signal"],
        "macd_histogram": macd_data["histogram"],
        "vwap": vwap,
        "bollinger_upper": bollinger["upper"],
        "bollinger_middle": bollinger["middle"],
        "bollinger_lower": bollinger["lower"],
        "momentum": momentum,
        "volume_delta": vol_delta["delta"],
        "volume_sma_ratio": vol_delta["sma_ratio"],
        "atr": atr,
        "obv_trend": obv,
        "price_vs_vwap": price_vs_vwap,
        "current_price": current_price,
    }
