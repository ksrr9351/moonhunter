from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
import time


class SignalType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class TradingSignal(BaseModel):
    symbol: str
    signal: SignalType = SignalType.HOLD
    confidence: float = Field(0.0, ge=0, le=100, description="Trade confidence 0-100%")
    pump_dump_risk: float = Field(0.0, ge=0, le=100, description="Pump/dump risk 0-100%")
    movement_strength: float = Field(0.0, description="Movement strength score")
    volume_anomaly: bool = False
    timestamp: int = Field(default_factory=lambda: int(time.time()))

    name: Optional[str] = None
    price: Optional[float] = None
    indicators: Optional[Dict[str, Any]] = None
    reasons: Optional[List[str]] = None
    risk_level: Optional[str] = None


class OHLCVCandle(BaseModel):
    symbol: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    timeframe: str = "5m"


class IndicatorSet(BaseModel):
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    vwap: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    bollinger_middle: Optional[float] = None
    momentum: Optional[float] = None
    volume_delta: Optional[float] = None
    volume_sma_ratio: Optional[float] = None
    atr: Optional[float] = None
    obv_trend: Optional[float] = None
    price_vs_vwap: Optional[float] = None


class AnomalyResult(BaseModel):
    is_anomaly: bool = False
    anomaly_score: float = 0.0
    volume_anomaly: bool = False
    price_anomaly: bool = False
    volume_zscore: float = 0.0
    price_zscore: float = 0.0
    isolation_score: Optional[float] = None


class PumpDumpResult(BaseModel):
    risk_percentage: float = 0.0
    is_pump: bool = False
    is_dump: bool = False
    pattern_type: Optional[str] = None
    volume_surge_ratio: float = 0.0
    price_velocity: float = 0.0
    reversal_probability: float = 0.0
    reasons: List[str] = []
