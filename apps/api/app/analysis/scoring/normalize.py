"""Normalization helpers: convert raw indicator values into [0,1] using
documented thresholds and capped piecewise-linear functions.
"""

from __future__ import annotations

import math


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def linear(raw: float, lo: float, hi: float) -> float:
    """Map raw in [lo, hi] linearly into [0,1], capped beyond."""
    if hi <= lo:
        return 1.0 if raw >= hi else 0.0
    return clamp01((raw - lo) / (hi - lo))


def capped_ratio(numerator: float, denominator: float, cap: float = 1.0) -> float:
    """Ratio capped at `cap`; guard division by zero -> 0 coverage driver."""
    if denominator <= 0:
        return 0.0
    return clamp01((numerator / denominator) / cap)


def log_scale(raw: float, target: float, k: float = 1.0) -> float:
    """Logarithmic normalization for quantities that grow without bound."""
    if raw <= 0:
        return 0.0
    return clamp01(math.log1p(k * raw) / math.log1p(k * target))


def inverted(x: float) -> float:
    return 1.0 - clamp01(x)


def inverse_weighted(avg_coupling: float, max_coupling: float) -> float:
    """Higher average/max coupling -> lower maintainability contribution."""
    if max_coupling <= 0:
        return 1.0
    return clamp01(1.0 - avg_coupling / max_coupling)


def boolean(x: bool) -> float:
    return 1.0 if x else 0.0
