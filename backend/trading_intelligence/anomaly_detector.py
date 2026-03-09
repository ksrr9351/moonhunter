"""
ML-Powered Anomaly Detection
IsolationForest + statistical z-score methods for volume/price anomaly detection
Training is separated from inference for low per-call latency.
"""
import numpy as np
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

try:
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not available, using statistical-only anomaly detection")


class AnomalyDetector:

    VOLUME_ZSCORE_THRESHOLD = 2.5
    PRICE_ZSCORE_THRESHOLD = 2.5
    MIN_SAMPLES_FOR_ML = 30
    CONTAMINATION = 0.05

    def __init__(self):
        self.models: Dict[str, IsolationForest] = {}
        self.scalers: Dict[str, StandardScaler] = {}
        self.last_trained: Dict[str, datetime] = {}
        self.retrain_interval_seconds = 300
        self._warm = False

    def pre_warm(self, symbol: str, closes: np.ndarray, volumes: np.ndarray):
        if not SKLEARN_AVAILABLE or len(closes) < self.MIN_SAMPLES_FOR_ML:
            return

        now = datetime.now(timezone.utc)
        if symbol in self.last_trained:
            elapsed = (now - self.last_trained[symbol]).total_seconds()
            if elapsed < self.retrain_interval_seconds:
                return

        features = self._build_features(closes, volumes)
        if features is None or len(features) < self.MIN_SAMPLES_FOR_ML:
            return

        self._train_model(symbol, features)
        self._warm = True

    def pre_warm_batch(self, symbol_data: Dict[str, Dict[str, np.ndarray]]):
        trained = 0
        for symbol, data in symbol_data.items():
            closes = data.get("closes")
            volumes = data.get("volumes")
            if closes is not None and volumes is not None:
                self.pre_warm(symbol, closes, volumes)
                trained += 1
        if trained > 0:
            logger.info(f"Anomaly models pre-warmed for {trained} symbols ({len(self.models)} total models)")

    def detect(
        self,
        closes: np.ndarray,
        volumes: np.ndarray,
        symbol: str = "UNKNOWN",
    ) -> Dict[str, Any]:
        result = {
            "is_anomaly": False,
            "anomaly_score": 0.0,
            "volume_anomaly": False,
            "price_anomaly": False,
            "volume_zscore": 0.0,
            "price_zscore": 0.0,
            "isolation_score": None,
        }

        if len(closes) < 5 or len(volumes) < 5:
            return result

        vol_stats = self._volume_zscore(volumes)
        result["volume_zscore"] = vol_stats["zscore"]
        result["volume_anomaly"] = vol_stats["is_anomaly"]

        price_stats = self._price_zscore(closes)
        result["price_zscore"] = price_stats["zscore"]
        result["price_anomaly"] = price_stats["is_anomaly"]

        if SKLEARN_AVAILABLE and symbol in self.models:
            ml_result = self._inference_only(closes, volumes, symbol)
            result["isolation_score"] = ml_result["score"]
            if ml_result["is_anomaly"]:
                result["is_anomaly"] = True

        stat_score = max(
            abs(result["volume_zscore"]) / 5.0,
            abs(result["price_zscore"]) / 5.0,
        )
        stat_score = min(stat_score, 1.0)

        if result["isolation_score"] is not None:
            result["anomaly_score"] = round(
                0.6 * result["isolation_score"] + 0.4 * stat_score, 4
            )
        else:
            result["anomaly_score"] = round(stat_score, 4)

        if result["volume_anomaly"] or result["price_anomaly"]:
            result["is_anomaly"] = True

        return result

    def _volume_zscore(self, volumes: np.ndarray) -> Dict[str, Any]:
        if len(volumes) < 5:
            return {"zscore": 0.0, "is_anomaly": False}
        mean_vol = np.mean(volumes[:-1])
        std_vol = np.std(volumes[:-1])
        if std_vol == 0:
            return {"zscore": 0.0, "is_anomaly": False}
        zscore = (volumes[-1] - mean_vol) / std_vol
        return {
            "zscore": round(float(zscore), 4),
            "is_anomaly": abs(zscore) > self.VOLUME_ZSCORE_THRESHOLD,
        }

    def _price_zscore(self, closes: np.ndarray) -> Dict[str, Any]:
        if len(closes) < 5:
            return {"zscore": 0.0, "is_anomaly": False}
        returns = np.diff(closes) / closes[:-1]
        if len(returns) < 3:
            return {"zscore": 0.0, "is_anomaly": False}
        mean_ret = np.mean(returns[:-1])
        std_ret = np.std(returns[:-1])
        if std_ret == 0:
            return {"zscore": 0.0, "is_anomaly": False}
        zscore = (returns[-1] - mean_ret) / std_ret
        return {
            "zscore": round(float(zscore), 4),
            "is_anomaly": abs(zscore) > self.PRICE_ZSCORE_THRESHOLD,
        }

    def _inference_only(
        self, closes: np.ndarray, volumes: np.ndarray, symbol: str
    ) -> Dict[str, Any]:
        try:
            features = self._build_features(closes, volumes)
            if features is None or len(features) < 1:
                return {"score": None, "is_anomaly": False}

            scaler = self.scalers[symbol]
            model = self.models[symbol]

            latest = features[-1:].reshape(1, -1)
            latest_scaled = scaler.transform(latest)

            raw_score = model.decision_function(latest_scaled)[0]
            prediction = model.predict(latest_scaled)[0]

            normalized_score = max(0.0, min(1.0, 0.5 - raw_score))

            return {
                "score": round(float(normalized_score), 4),
                "is_anomaly": prediction == -1,
            }
        except Exception as e:
            logger.error(f"IsolationForest inference error for {symbol}: {e}")
            return {"score": None, "is_anomaly": False}

    def _build_features(self, closes: np.ndarray, volumes: np.ndarray) -> Optional[np.ndarray]:
        min_len = min(len(closes), len(volumes))
        if min_len < 10:
            return None
        closes = closes[-min_len:]
        volumes = volumes[-min_len:]

        returns = np.diff(closes) / (closes[:-1] + 1e-10)
        vol_changes = np.diff(volumes) / (volumes[:-1] + 1e-10)

        n = len(returns)
        if n < 5:
            return None

        features_list = []
        for i in range(4, n):
            window_ret = returns[i - 4:i + 1]
            window_vol = vol_changes[i - 4:i + 1] if i < len(vol_changes) else vol_changes[-5:]
            feat = np.array([
                returns[i],
                np.std(window_ret),
                np.mean(window_ret),
                vol_changes[i] if i < len(vol_changes) else 0,
                np.std(window_vol),
                np.mean(window_vol),
                abs(returns[i]) * (1 + abs(vol_changes[i] if i < len(vol_changes) else 0)),
            ])
            features_list.append(feat)

        if len(features_list) == 0:
            return None
        return np.array(features_list)

    def _train_model(self, symbol: str, features: np.ndarray):
        try:
            scaler = StandardScaler()
            scaled = scaler.fit_transform(features)

            model = IsolationForest(
                n_estimators=100,
                contamination=self.CONTAMINATION,
                random_state=42,
                n_jobs=1,
            )
            model.fit(scaled)

            self.models[symbol] = model
            self.scalers[symbol] = scaler
            self.last_trained[symbol] = datetime.now(timezone.utc)
            logger.debug(f"IsolationForest trained for {symbol} with {len(features)} samples")
        except Exception as e:
            logger.error(f"Model training error for {symbol}: {e}")


anomaly_detector = AnomalyDetector()
