"""
Enhanced Pump/Dump Detector
Multi-factor analysis: volume surge, price velocity, reversal patterns, liquidity traps
"""
import numpy as np
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class PumpDumpDetector:

    VOLUME_SURGE_THRESHOLD = 3.0
    PRICE_VELOCITY_PUMP = 3.0
    PRICE_VELOCITY_DUMP = -3.0
    RAPID_REVERSAL_WINDOW = 5
    LIQUIDITY_TRAP_VOL_RATIO = 5.0

    def analyze(
        self,
        closes: np.ndarray,
        volumes: np.ndarray,
        highs: np.ndarray,
        lows: np.ndarray,
        change_1h: float = 0.0,
        change_24h: float = 0.0,
    ) -> Dict[str, Any]:
        result = {
            "risk_percentage": 0.0,
            "is_pump": False,
            "is_dump": False,
            "pattern_type": None,
            "volume_surge_ratio": 0.0,
            "price_velocity": 0.0,
            "reversal_probability": 0.0,
            "reasons": [],
        }

        if len(closes) < 5:
            return result

        scores = []

        vol_score, vol_info = self._volume_surge_analysis(volumes)
        scores.append(("volume_surge", vol_score, 0.25))
        result["volume_surge_ratio"] = vol_info["surge_ratio"]
        if vol_score > 0.5:
            result["reasons"].append(f"Volume surge {vol_info['surge_ratio']:.1f}x above average")

        vel_score, vel_info = self._price_velocity_analysis(closes)
        scores.append(("price_velocity", vel_score, 0.25))
        result["price_velocity"] = vel_info["velocity"]
        if vel_score > 0.5:
            direction = "up" if vel_info["velocity"] > 0 else "down"
            result["reasons"].append(f"Rapid price movement {direction} ({vel_info['velocity']:.2f}% velocity)")

        rev_score, rev_info = self._reversal_pattern_analysis(closes, volumes)
        scores.append(("reversal", rev_score, 0.20))
        result["reversal_probability"] = rev_info["probability"]
        if rev_score > 0.5:
            result["reasons"].append(f"Reversal pattern detected ({rev_info['pattern']})")

        trap_score, trap_info = self._liquidity_trap_analysis(closes, volumes, highs, lows)
        scores.append(("liquidity_trap", trap_score, 0.15))
        if trap_score > 0.5:
            result["reasons"].append(f"Possible liquidity trap: {trap_info['type']}")

        ext_score = self._external_change_score(change_1h, change_24h)
        scores.append(("external_momentum", ext_score, 0.15))
        if ext_score > 0.5:
            result["reasons"].append(f"Extreme momentum: 1h={change_1h:+.1f}%, 24h={change_24h:+.1f}%")

        total_weight = sum(w for _, _, w in scores)
        risk = sum(s * w for _, s, w in scores) / total_weight if total_weight > 0 else 0
        result["risk_percentage"] = round(risk * 100, 2)

        velocity = result["price_velocity"]
        if risk > 0.5 and velocity > 0:
            result["is_pump"] = True
            result["pattern_type"] = "pump"
        elif risk > 0.5 and velocity < 0:
            result["is_dump"] = True
            result["pattern_type"] = "dump"
        elif risk > 0.4 and abs(velocity) > self.PRICE_VELOCITY_PUMP:
            if velocity > 0:
                result["is_pump"] = True
                result["pattern_type"] = "possible_pump"
            else:
                result["is_dump"] = True
                result["pattern_type"] = "possible_dump"

        if result["is_pump"] and result["reversal_probability"] > 0.6:
            result["pattern_type"] = "pump_and_dump"
            result["reasons"].append("High reversal probability after pump - likely pump & dump scheme")

        return result

    def _volume_surge_analysis(self, volumes: np.ndarray) -> tuple:
        if len(volumes) < 10:
            return 0.0, {"surge_ratio": 1.0}
        baseline = np.mean(volumes[:-3])
        if baseline == 0:
            return 0.0, {"surge_ratio": 1.0}
        recent_avg = np.mean(volumes[-3:])
        surge_ratio = recent_avg / baseline

        if surge_ratio >= self.LIQUIDITY_TRAP_VOL_RATIO:
            score = 1.0
        elif surge_ratio >= self.VOLUME_SURGE_THRESHOLD:
            score = 0.6 + 0.4 * min((surge_ratio - self.VOLUME_SURGE_THRESHOLD) / 5.0, 1.0)
        elif surge_ratio >= 2.0:
            score = 0.3 + 0.3 * (surge_ratio - 2.0) / (self.VOLUME_SURGE_THRESHOLD - 2.0)
        else:
            score = max(0.0, (surge_ratio - 1.0) * 0.3)

        return round(score, 4), {"surge_ratio": round(surge_ratio, 2)}

    def _price_velocity_analysis(self, closes: np.ndarray) -> tuple:
        if len(closes) < 5:
            return 0.0, {"velocity": 0.0}
        returns = np.diff(closes[-6:]) / closes[-6:-1] * 100
        velocity = np.mean(returns[-3:])
        acceleration = returns[-1] - returns[-2] if len(returns) >= 2 else 0

        abs_vel = abs(velocity)
        if abs_vel >= 5.0:
            score = 1.0
        elif abs_vel >= self.PRICE_VELOCITY_PUMP:
            score = 0.6 + 0.4 * (abs_vel - self.PRICE_VELOCITY_PUMP) / 2.0
        elif abs_vel >= 1.5:
            score = 0.2 + 0.4 * (abs_vel - 1.5) / 1.5
        else:
            score = abs_vel * 0.13

        if abs(acceleration) > abs_vel * 0.5:
            score = min(1.0, score * 1.2)

        return round(min(score, 1.0), 4), {"velocity": round(velocity, 4)}

    def _reversal_pattern_analysis(self, closes: np.ndarray, volumes: np.ndarray) -> tuple:
        if len(closes) < self.RAPID_REVERSAL_WINDOW + 2:
            return 0.0, {"probability": 0.0, "pattern": "none"}

        window = closes[-self.RAPID_REVERSAL_WINDOW:]
        returns = np.diff(window) / window[:-1] * 100

        positive = returns[returns > 0]
        negative = returns[returns < 0]

        if len(positive) >= 2 and len(negative) >= 1:
            if returns[-1] < 0 and np.mean(returns[:-1]) > 0:
                pump_magnitude = np.sum(positive)
                dump_magnitude = abs(np.sum(negative))
                vol_pattern = volumes[-3:] if len(volumes) >= 3 else volumes

                if np.mean(vol_pattern) > np.mean(volumes[:-3]) * 2 if len(volumes) > 3 else False:
                    prob = min(1.0, (dump_magnitude / (pump_magnitude + 1e-10)) * 0.8 + 0.2)
                else:
                    prob = min(0.8, (dump_magnitude / (pump_magnitude + 1e-10)) * 0.6)

                return round(prob, 4), {"probability": round(prob, 4), "pattern": "pump_reversal"}

        if len(negative) >= 2 and len(positive) >= 1:
            if returns[-1] > 0 and np.mean(returns[:-1]) < 0:
                prob = 0.3
                return prob, {"probability": prob, "pattern": "dead_cat_bounce"}

        sign_changes = np.sum(np.diff(np.sign(returns)) != 0)
        if sign_changes >= 3:
            return 0.4, {"probability": 0.4, "pattern": "choppy_reversal"}

        return 0.0, {"probability": 0.0, "pattern": "none"}

    def _liquidity_trap_analysis(
        self, closes: np.ndarray, volumes: np.ndarray, highs: np.ndarray, lows: np.ndarray
    ) -> tuple:
        if len(closes) < 5:
            return 0.0, {"type": "none"}

        recent_range = highs[-3:].max() - lows[-3:].min()
        avg_range = np.mean(highs[:-3] - lows[:-3]) if len(highs) > 3 else recent_range

        if avg_range > 0:
            range_expansion = recent_range / avg_range
        else:
            range_expansion = 1.0

        vol_baseline = np.mean(volumes[:-3]) if len(volumes) > 3 else np.mean(volumes)
        vol_ratio = np.mean(volumes[-3:]) / vol_baseline if vol_baseline > 0 else 1.0

        if range_expansion > 2.0 and vol_ratio > self.LIQUIDITY_TRAP_VOL_RATIO:
            wicks = (highs[-3:] - closes[-3:]) + (closes[-3:] - lows[-3:])
            bodies = np.abs(closes[-3:] - np.roll(closes[-3:], 1)[1:])
            if len(bodies) > 0 and np.mean(bodies) > 0:
                wick_body_ratio = np.mean(wicks[-len(bodies):]) / np.mean(bodies)
                if wick_body_ratio > 3.0:
                    return 0.8, {"type": "wick_trap"}

            return 0.6, {"type": "volatility_trap"}

        if vol_ratio > self.VOLUME_SURGE_THRESHOLD and range_expansion < 0.5:
            return 0.5, {"type": "absorption"}

        return 0.0, {"type": "none"}

    def _external_change_score(self, change_1h: float, change_24h: float) -> float:
        max_change = max(abs(change_1h), abs(change_24h) * 0.5)
        if max_change >= 10:
            return 1.0
        elif max_change >= 5:
            return 0.6 + 0.4 * (max_change - 5) / 5
        elif max_change >= 3:
            return 0.3 + 0.3 * (max_change - 3) / 2
        return max_change * 0.1


pump_dump_detector = PumpDumpDetector()
