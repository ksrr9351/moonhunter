"""
Signal Engine - AI-enhanced buy/sell signal generation
Combines technical indicators, anomaly detection, and pump/dump analysis
into a unified confidence-scored trading signal
"""
import numpy as np
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import GradientBoostingClassifier
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class SignalEngine:

    def __init__(self):
        self.ml_model = None
        self.ml_scaler = None
        self.training_buffer: List[Dict] = []
        self.min_training_samples = 50
        self.model_trained = False
        self._seeded_only = False

    def generate_signal(
        self,
        indicators: Dict[str, Any],
        anomaly: Dict[str, Any],
        pump_dump: Dict[str, Any],
        change_1h: float = 0.0,
        change_24h: float = 0.0,
        change_7d: float = 0.0,
        market_cap: float = 0,
        volume_24h: float = 0,
    ) -> Dict[str, Any]:
        rule_signal = self._rule_based_signal(indicators, change_1h, change_24h)

        pd_risk = pump_dump.get("risk_percentage", 0)
        vol_anomaly = anomaly.get("volume_anomaly", False)
        anomaly_score = anomaly.get("anomaly_score", 0)

        signal = rule_signal["signal"]
        base_confidence = rule_signal["confidence"]
        reasons = list(rule_signal["reasons"])

        if pd_risk > 60:
            if signal == "BUY" and pump_dump.get("is_pump"):
                signal = "HOLD"
                base_confidence *= 0.4
                reasons.append(f"BUY downgraded: pump risk {pd_risk:.0f}%")
            elif signal == "SELL" and pump_dump.get("is_dump"):
                base_confidence *= 1.15
                reasons.append(f"SELL confirmed: dump detected {pd_risk:.0f}%")
        elif pd_risk > 40:
            base_confidence *= 0.85
            reasons.append(f"Moderate pump/dump risk: {pd_risk:.0f}%")

        if vol_anomaly:
            if signal == "BUY":
                base_confidence *= 0.8
                reasons.append("Volume anomaly detected - proceed with caution")
            elif signal == "SELL":
                base_confidence *= 1.1
                reasons.append("Volume anomaly supports exit signal")

        if anomaly_score > 0.7:
            base_confidence *= 0.75
            reasons.append(f"High anomaly score: {anomaly_score:.2f}")

        quality_mult = self._market_quality_multiplier(market_cap, volume_24h)
        base_confidence *= quality_mult

        movement_strength = self._calculate_movement_strength(
            indicators, change_1h, change_24h, anomaly
        )

        ml_adjustment = self._ml_confidence_adjustment(
            indicators, anomaly, pump_dump, change_1h, change_24h
        )
        if ml_adjustment is not None:
            ml_weight = 0.15 if self._seeded_only else 0.3
            base_confidence = (1 - ml_weight) * base_confidence + ml_weight * ml_adjustment
            reasons.append(f"AI confidence adjustment: {ml_adjustment:.0f}%")

        confidence = max(5.0, min(95.0, base_confidence))

        risk_level = "low"
        if pd_risk > 60 or anomaly_score > 0.7:
            risk_level = "high"
        elif pd_risk > 30 or anomaly_score > 0.4:
            risk_level = "medium"

        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "movement_strength": round(movement_strength, 4),
            "risk_level": risk_level,
            "reasons": reasons,
            "rule_signal": rule_signal["signal"],
            "rule_confidence": round(rule_signal["confidence"], 2),
        }

    def _rule_based_signal(self, indicators: Dict[str, Any], change_1h: float, change_24h: float) -> Dict[str, Any]:
        buy_score = 0.0
        sell_score = 0.0
        reasons = []

        rsi = indicators.get("rsi")
        if rsi is not None:
            if rsi < 30:
                buy_score += 25
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi < 40:
                buy_score += 10
                reasons.append(f"RSI approaching oversold ({rsi:.1f})")
            elif rsi > 70:
                sell_score += 25
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 60:
                sell_score += 10
                reasons.append(f"RSI approaching overbought ({rsi:.1f})")

        macd = indicators.get("macd")
        macd_signal = indicators.get("macd_signal")
        histogram = indicators.get("macd_histogram")
        if macd is not None and macd_signal is not None:
            if macd > macd_signal:
                buy_score += 15
                reasons.append("MACD bullish crossover")
            else:
                sell_score += 15
                reasons.append("MACD bearish crossover")
            if histogram is not None:
                if histogram > 0 and abs(histogram) > abs(macd) * 0.1:
                    buy_score += 5
                elif histogram < 0 and abs(histogram) > abs(macd) * 0.1:
                    sell_score += 5

        price_vs_vwap = indicators.get("price_vs_vwap")
        if price_vs_vwap is not None:
            if price_vs_vwap < -2:
                buy_score += 15
                reasons.append(f"Price below VWAP ({price_vs_vwap:+.2f}%)")
            elif price_vs_vwap > 2:
                sell_score += 15
                reasons.append(f"Price above VWAP ({price_vs_vwap:+.2f}%)")

        bb_upper = indicators.get("bollinger_upper")
        bb_lower = indicators.get("bollinger_lower")
        current_price = indicators.get("current_price", 0)
        if bb_upper and bb_lower and current_price:
            bb_range = bb_upper - bb_lower
            if bb_range > 0:
                position = (current_price - bb_lower) / bb_range
                if position < 0.1:
                    buy_score += 15
                    reasons.append("Price at lower Bollinger Band")
                elif position > 0.9:
                    sell_score += 15
                    reasons.append("Price at upper Bollinger Band")

        momentum = indicators.get("momentum")
        if momentum is not None:
            if momentum < -5:
                buy_score += 10
                reasons.append(f"Negative momentum reversal opportunity ({momentum:.1f}%)")
            elif momentum > 5:
                sell_score += 10
                reasons.append(f"Strong positive momentum ({momentum:.1f}%)")

        vol_delta = indicators.get("volume_delta")
        if vol_delta is not None:
            if vol_delta > 30:
                buy_score += 10
                reasons.append(f"Strong buying pressure ({vol_delta:.0f}%)")
            elif vol_delta < -30:
                sell_score += 10
                reasons.append(f"Strong selling pressure ({vol_delta:.0f}%)")

        vol_sma_ratio = indicators.get("volume_sma_ratio")
        if vol_sma_ratio is not None and vol_sma_ratio > 2.0:
            score_boost = min(10, (vol_sma_ratio - 2.0) * 5)
            if buy_score > sell_score:
                buy_score += score_boost
            else:
                sell_score += score_boost
            reasons.append(f"Volume {vol_sma_ratio:.1f}x above average")

        obv = indicators.get("obv_trend")
        if obv is not None:
            if obv > 0.1:
                buy_score += 5
            elif obv < -0.1:
                sell_score += 5

        total = buy_score + sell_score
        if total == 0:
            return {"signal": "HOLD", "confidence": 50.0, "reasons": ["Insufficient data for signal"]}

        if buy_score > sell_score and buy_score >= 25:
            signal = "BUY"
            confidence = min(90, 40 + buy_score - sell_score * 0.5)
        elif sell_score > buy_score and sell_score >= 25:
            signal = "SELL"
            confidence = min(90, 40 + sell_score - buy_score * 0.5)
        else:
            signal = "HOLD"
            confidence = max(30, 50 - abs(buy_score - sell_score))

        return {"signal": signal, "confidence": confidence, "reasons": reasons}

    def _calculate_movement_strength(
        self,
        indicators: Dict[str, Any],
        change_1h: float,
        change_24h: float,
        anomaly: Dict[str, Any],
    ) -> float:
        components = []
        momentum = indicators.get("momentum")
        if momentum is not None:
            components.append(abs(momentum) / 10.0)
        components.append(abs(change_1h) / 5.0)
        components.append(abs(change_24h) / 10.0)

        vol_ratio = indicators.get("volume_sma_ratio")
        if vol_ratio is not None:
            components.append(min(1.0, (vol_ratio - 1.0) / 3.0) if vol_ratio > 1 else 0)

        anomaly_score = anomaly.get("anomaly_score", 0)
        components.append(anomaly_score * 0.5)

        if not components:
            return 0.0
        raw = np.mean(components)
        return min(1.0, max(0.0, raw))

    def _market_quality_multiplier(self, market_cap: float, volume_24h: float) -> float:
        mult = 1.0
        if market_cap > 10_000_000_000:
            mult *= 1.1
        elif market_cap > 1_000_000_000:
            mult *= 1.05
        elif market_cap < 100_000_000:
            mult *= 0.85
        elif market_cap < 10_000_000:
            mult *= 0.7

        if volume_24h > 0 and market_cap > 0:
            vol_ratio = volume_24h / market_cap
            if vol_ratio < 0.005:
                mult *= 0.85
            elif vol_ratio > 0.3:
                mult *= 0.9
        return mult

    def _ml_confidence_adjustment(
        self,
        indicators: Dict[str, Any],
        anomaly: Dict[str, Any],
        pump_dump: Dict[str, Any],
        change_1h: float,
        change_24h: float,
    ) -> Optional[float]:
        if not SKLEARN_AVAILABLE or not self.model_trained:
            return None

        try:
            features = self._extract_ml_features(indicators, anomaly, pump_dump, change_1h, change_24h)
            if features is None:
                return None

            scaled = self.ml_scaler.transform([features])
            probas = self.ml_model.predict_proba(scaled)[0]
            max_proba = max(probas) * 100
            return max_proba
        except Exception as e:
            logger.debug(f"ML adjustment error: {e}")
            return None

    def _extract_ml_features(
        self,
        indicators: Dict[str, Any],
        anomaly: Dict[str, Any],
        pump_dump: Dict[str, Any],
        change_1h: float,
        change_24h: float,
    ) -> Optional[list]:
        rsi = indicators.get("rsi", 50)
        macd = indicators.get("macd", 0) or 0
        momentum = indicators.get("momentum", 0) or 0
        vol_delta = indicators.get("volume_delta", 0) or 0
        vol_ratio = indicators.get("volume_sma_ratio", 1) or 1
        obv = indicators.get("obv_trend", 0) or 0
        anomaly_score = anomaly.get("anomaly_score", 0)
        pd_risk = pump_dump.get("risk_percentage", 0)

        return [rsi, macd, momentum, vol_delta, vol_ratio, obv, anomaly_score, pd_risk, change_1h, change_24h]

    def seed_model(self):
        if not SKLEARN_AVAILABLE:
            logger.warning("sklearn not available - ML seeding skipped")
            return False
        if self.model_trained:
            logger.info("ML model already trained - seeding skipped")
            return True

        try:
            from trading_intelligence.ml_seed_data import generate_seed_data
            seed_samples = generate_seed_data(total_samples=300)

            for features, label in seed_samples:
                self.training_buffer.append({"features": features, "label": label})

            self._train_model()

            if self.model_trained:
                self._seeded_only = True
                logger.info(f"Signal ML model seeded and trained with {len(seed_samples)} historical samples (seed-only mode, 15% blend weight)")
                return True
            else:
                logger.warning("ML model seeding completed but training failed")
                return False
        except Exception as e:
            logger.error(f"ML model seeding error: {e}")
            return False

    def add_training_sample(self, features: list, label: int):
        self.training_buffer.append({"features": features, "label": label})
        if len(self.training_buffer) >= self.min_training_samples:
            self._train_model()
            if self.model_trained:
                self._seeded_only = False

    def _train_model(self):
        if not SKLEARN_AVAILABLE or len(self.training_buffer) < self.min_training_samples:
            return
        try:
            X = np.array([s["features"] for s in self.training_buffer])
            y = np.array([s["label"] for s in self.training_buffer])

            self.ml_scaler = StandardScaler()
            X_scaled = self.ml_scaler.fit_transform(X)

            self.ml_model = GradientBoostingClassifier(
                n_estimators=50,
                max_depth=3,
                learning_rate=0.1,
                random_state=42,
            )
            self.ml_model.fit(X_scaled, y)
            self.model_trained = True
            logger.info(f"Signal ML model trained with {len(X)} samples")
        except Exception as e:
            logger.error(f"ML model training error: {e}")


signal_engine = SignalEngine()
