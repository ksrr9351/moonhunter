"""
ML Seed Data Generator - Bootstrap GradientBoosting model with historically-grounded labeled data.

Generates realistic training samples based on well-established technical analysis patterns:
- RSI oversold/overbought zones
- MACD bullish/bearish crossovers
- Volume surge patterns
- Momentum divergences
- Pump/dump risk scenarios
- Ambiguous/borderline cases for calibration

Feature vector: [rsi, macd, momentum, vol_delta, vol_ratio, obv, anomaly_score, pd_risk, change_1h, change_24h]
Labels: 0=SELL, 1=HOLD, 2=BUY
"""
import numpy as np
from typing import List, Tuple

LABEL_SELL = 0
LABEL_HOLD = 1
LABEL_BUY = 2

rng = np.random.RandomState(42)


def _jitter(base: float, spread: float) -> float:
    return base + rng.uniform(-spread, spread)


def _generate_buy_samples(n: int) -> List[Tuple[list, int]]:
    samples = []
    per_pattern = max(1, n // 6)

    for _ in range(per_pattern):
        samples.append(([
            _jitter(25, 5), _jitter(0.5, 0.3), _jitter(-3, 2), _jitter(20, 15),
            _jitter(1.2, 0.3), _jitter(0.15, 0.1), _jitter(0.15, 0.1),
            _jitter(10, 8), _jitter(-2, 1.5), _jitter(-5, 3),
        ], LABEL_BUY))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(35, 5), _jitter(1.0, 0.5), _jitter(2, 2), _jitter(35, 10),
            _jitter(2.5, 0.5), _jitter(0.25, 0.1), _jitter(0.1, 0.08),
            _jitter(5, 4), _jitter(3, 2), _jitter(8, 4),
        ], LABEL_BUY))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(30, 4), _jitter(0.8, 0.4), _jitter(5, 3), _jitter(15, 10),
            _jitter(1.5, 0.4), _jitter(0.2, 0.08), _jitter(0.05, 0.04),
            _jitter(3, 3), _jitter(1, 1), _jitter(-8, 3),
        ], LABEL_BUY))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(40, 5), _jitter(0.3, 0.2), _jitter(3, 2), _jitter(25, 10),
            _jitter(1.8, 0.4), _jitter(0.1, 0.05), _jitter(0.2, 0.1),
            _jitter(8, 5), _jitter(2, 1.5), _jitter(3, 3),
        ], LABEL_BUY))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(22, 4), _jitter(-0.2, 0.3), _jitter(-6, 3), _jitter(10, 8),
            _jitter(1.0, 0.3), _jitter(0.05, 0.05), _jitter(0.3, 0.15),
            _jitter(15, 8), _jitter(-4, 2), _jitter(-10, 4),
        ], LABEL_BUY))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(42, 8), _jitter(0.15, 0.25), _jitter(1, 3), _jitter(8, 12),
            _jitter(1.3, 0.4), _jitter(0.08, 0.08), _jitter(0.18, 0.12),
            _jitter(18, 12), _jitter(-0.5, 2), _jitter(-2, 4),
        ], LABEL_BUY))

    return samples


def _generate_sell_samples(n: int) -> List[Tuple[list, int]]:
    samples = []
    per_pattern = max(1, n // 6)

    for _ in range(per_pattern):
        samples.append(([
            _jitter(75, 5), _jitter(-0.5, 0.3), _jitter(6, 3), _jitter(-20, 10),
            _jitter(1.2, 0.3), _jitter(-0.15, 0.1), _jitter(0.15, 0.1),
            _jitter(10, 8), _jitter(5, 2), _jitter(12, 5),
        ], LABEL_SELL))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(65, 5), _jitter(-1.0, 0.5), _jitter(-2, 3), _jitter(-35, 10),
            _jitter(2.5, 0.5), _jitter(-0.25, 0.1), _jitter(0.1, 0.08),
            _jitter(5, 4), _jitter(-3, 2), _jitter(-8, 4),
        ], LABEL_SELL))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(72, 4), _jitter(-0.8, 0.4), _jitter(8, 3), _jitter(-15, 10),
            _jitter(3.0, 0.5), _jitter(-0.2, 0.08), _jitter(0.6, 0.2),
            _jitter(55, 15), _jitter(8, 3), _jitter(20, 8),
        ], LABEL_SELL))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(68, 5), _jitter(-0.6, 0.3), _jitter(4, 2), _jitter(-25, 10),
            _jitter(1.5, 0.4), _jitter(-0.18, 0.08), _jitter(0.4, 0.15),
            _jitter(40, 12), _jitter(6, 3), _jitter(15, 6),
        ], LABEL_SELL))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(80, 4), _jitter(-1.2, 0.5), _jitter(10, 3), _jitter(-30, 8),
            _jitter(2.0, 0.5), _jitter(-0.3, 0.1), _jitter(0.25, 0.1),
            _jitter(20, 10), _jitter(4, 2), _jitter(18, 5),
        ], LABEL_SELL))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(58, 8), _jitter(-0.15, 0.25), _jitter(2, 3), _jitter(-10, 12),
            _jitter(1.3, 0.4), _jitter(-0.08, 0.08), _jitter(0.2, 0.12),
            _jitter(22, 12), _jitter(2, 2.5), _jitter(5, 5),
        ], LABEL_SELL))

    return samples


def _generate_hold_samples(n: int) -> List[Tuple[list, int]]:
    samples = []
    per_pattern = max(1, n // 5)

    for _ in range(per_pattern):
        samples.append(([
            _jitter(50, 8), _jitter(0.0, 0.2), _jitter(0, 2), _jitter(0, 10),
            _jitter(1.0, 0.2), _jitter(0.0, 0.05), _jitter(0.05, 0.04),
            _jitter(5, 4), _jitter(0, 1), _jitter(0, 2),
        ], LABEL_HOLD))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(45, 10), _jitter(0.1, 0.15), _jitter(1, 1.5), _jitter(5, 8),
            _jitter(1.1, 0.2), _jitter(0.02, 0.03), _jitter(0.08, 0.05),
            _jitter(15, 10), _jitter(0.5, 1), _jitter(1, 3),
        ], LABEL_HOLD))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(55, 5), _jitter(-0.1, 0.15), _jitter(-1, 1.5), _jitter(-5, 8),
            _jitter(0.9, 0.2), _jitter(-0.02, 0.03), _jitter(0.12, 0.08),
            _jitter(20, 8), _jitter(-0.5, 1), _jitter(-2, 3),
        ], LABEL_HOLD))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(48, 6), _jitter(0.05, 0.1), _jitter(0.5, 1), _jitter(2, 5),
            _jitter(1.05, 0.15), _jitter(0.01, 0.02), _jitter(0.35, 0.15),
            _jitter(30, 10), _jitter(0, 0.8), _jitter(0, 1.5),
        ], LABEL_HOLD))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(52, 12), _jitter(0.0, 0.3), _jitter(0, 3), _jitter(0, 15),
            _jitter(1.1, 0.4), _jitter(0.0, 0.08), _jitter(0.15, 0.12),
            _jitter(18, 14), _jitter(0, 2), _jitter(0, 4),
        ], LABEL_HOLD))

    return samples


def _generate_ambiguous_samples(n: int) -> List[Tuple[list, int]]:
    samples = []
    per_pattern = max(1, n // 6)

    for _ in range(per_pattern):
        samples.append(([
            _jitter(38, 6), _jitter(0.2, 0.4), _jitter(-1, 3), _jitter(10, 15),
            _jitter(1.3, 0.5), _jitter(0.05, 0.1), _jitter(0.2, 0.15),
            _jitter(20, 15), _jitter(-1, 2), _jitter(-3, 4),
        ], rng.choice([LABEL_BUY, LABEL_HOLD])))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(62, 6), _jitter(-0.2, 0.4), _jitter(2, 3), _jitter(-10, 15),
            _jitter(1.3, 0.5), _jitter(-0.05, 0.1), _jitter(0.2, 0.15),
            _jitter(20, 15), _jitter(2, 2), _jitter(4, 4),
        ], rng.choice([LABEL_SELL, LABEL_HOLD])))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(50, 15), _jitter(0.0, 0.5), _jitter(0, 4), _jitter(0, 20),
            _jitter(1.2, 0.5), _jitter(0.0, 0.1), _jitter(0.3, 0.2),
            _jitter(25, 18), _jitter(0, 3), _jitter(0, 6),
        ], rng.choice([LABEL_BUY, LABEL_SELL, LABEL_HOLD])))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(30, 8), _jitter(-0.3, 0.5), _jitter(-2, 4), _jitter(-5, 15),
            _jitter(1.8, 0.6), _jitter(-0.05, 0.12), _jitter(0.4, 0.2),
            _jitter(35, 15), _jitter(-2, 3), _jitter(-4, 5),
        ], rng.choice([LABEL_BUY, LABEL_HOLD])))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(70, 8), _jitter(0.3, 0.5), _jitter(3, 4), _jitter(5, 15),
            _jitter(1.8, 0.6), _jitter(0.05, 0.12), _jitter(0.35, 0.2),
            _jitter(30, 15), _jitter(3, 3), _jitter(8, 5),
        ], rng.choice([LABEL_SELL, LABEL_HOLD])))

    for _ in range(per_pattern):
        samples.append(([
            _jitter(45, 10), _jitter(0.1, 0.3), _jitter(1, 3), _jitter(5, 12),
            _jitter(1.5, 0.5), _jitter(0.03, 0.08), _jitter(0.25, 0.15),
            _jitter(15, 12), _jitter(1, 2), _jitter(2, 4),
        ], rng.choice([LABEL_BUY, LABEL_SELL, LABEL_HOLD])))

    return samples


def generate_seed_data(total_samples: int = 300) -> List[Tuple[list, int]]:
    core_per_class = total_samples // 4
    ambiguous_count = total_samples - core_per_class * 3

    samples = []
    samples.extend(_generate_buy_samples(core_per_class))
    samples.extend(_generate_sell_samples(core_per_class))
    samples.extend(_generate_hold_samples(core_per_class))
    samples.extend(_generate_ambiguous_samples(ambiguous_count))

    rng.shuffle(samples)
    return samples
