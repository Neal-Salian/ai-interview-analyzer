"""
Scoring utilities — shared helpers for confidence-weighted metric scoring.

Every metric plugin imports from here to ensure consistent, reliable scoring.
Centralises the confidence-weighting math so individual metrics stay simple.

Key concepts:
- Each signal produces a (score, confidence) pair instead of just a score.
- confidence_weighted_average() combines them, weighting by confidence.
- sample_size_confidence() gates signals on minimum data thresholds.
- remove_outliers_iqr() and ema_smooth() reduce noise before scoring.

All functions are pure, deterministic, and have no external dependencies.
"""

from __future__ import annotations

import math
from typing import TypedDict


# ── Types ─────────────────────────────────────────────────────────────────────

class SignalComponent(TypedDict, total=False):
    """One scored signal with its confidence."""
    score: int            # 0–100
    confidence: float     # 0.0–1.0
    signal_name: str      # e.g. "emotion_stability"


class WeightedResult(TypedDict):
    """Result of confidence_weighted_average()."""
    final_score: int          # 0–100, confidence-weighted
    raw_score: int            # 0–100, simple average (for auditing)
    overall_confidence: float # 0.0–1.0
    confidence_details: list[dict]  # per-signal breakdown


# ── Confidence-weighted aggregation ───────────────────────────────────────────

def confidence_weighted_average(
    components: list[SignalComponent],
    min_confidence: float = 0.1,
) -> WeightedResult:
    """
    Combine multiple (score, confidence) pairs into a single weighted score.

    Drops components with confidence < min_confidence entirely.
    Returns both the weighted score and the raw (unweighted) average for auditing.

    If no components survive the confidence filter, returns score=0, confidence=0.
    """
    # Filter out unreliable signals
    valid = [c for c in components if c.get("confidence", 0) >= min_confidence]

    if not valid:
        return WeightedResult(
            final_score=0,
            raw_score=0,
            overall_confidence=0.0,
            confidence_details=[],
        )

    # Raw (unweighted) average — for auditing / comparison
    raw_score = int(sum(c["score"] for c in valid) / len(valid))

    # Confidence-weighted average
    total_weight = sum(c["confidence"] for c in valid)
    if total_weight <= 0:
        weighted_score = raw_score
    else:
        weighted_score = int(
            sum(c["score"] * c["confidence"] for c in valid) / total_weight
        )

    # Clamp
    weighted_score = max(0, min(100, weighted_score))
    raw_score = max(0, min(100, raw_score))

    # Overall confidence: average of component confidences, scaled by how
    # many of the original components survived filtering.
    survival_ratio = len(valid) / max(len(components), 1)
    avg_confidence = sum(c["confidence"] for c in valid) / len(valid)
    overall_confidence = round(avg_confidence * survival_ratio, 3)

    # Per-signal breakdown
    details = []
    for c in valid:
        weight = c["confidence"] / total_weight if total_weight > 0 else 0
        details.append({
            "signal": c.get("signal_name", "unknown"),
            "score": c["score"],
            "confidence": round(c["confidence"], 3),
            "weight_applied": round(weight, 3),
        })

    return WeightedResult(
        final_score=weighted_score,
        raw_score=raw_score,
        overall_confidence=overall_confidence,
        confidence_details=details,
    )


# ── Sample-size confidence ────────────────────────────────────────────────────

def sample_size_confidence(
    n: int,
    min_n: int,
    ideal_n: int,
) -> float:
    """
    Return a 0.0–1.0 confidence multiplier based on sample count.

    n < min_n  → 0.0  (signal should be dropped)
    n >= ideal_n → 1.0  (full confidence)
    between   → smooth linear ramp

    Examples:
        sample_size_confidence(3, 10, 50)  → 0.0  (below minimum)
        sample_size_confidence(30, 10, 50) → 0.5  (halfway)
        sample_size_confidence(50, 10, 50) → 1.0  (ideal)
    """
    if n < min_n:
        return 0.0
    if n >= ideal_n:
        return 1.0
    return round((n - min_n) / (ideal_n - min_n), 3)


# ── Keyword-density confidence ────────────────────────────────────────────────

def keyword_density_confidence(
    hits: int,
    word_count: int,
    min_words: int = 50,
    ideal_words: int = 200,
) -> float:
    """
    Confidence for keyword-density-based signals.

    Short transcripts produce unreliable keyword density — even a single
    keyword match in 10 words gives an inflated density. This function
    gates on minimum word count and scales confidence with transcript length.

    Returns 0.0 if word_count < min_words, regardless of hits.
    """
    if word_count < min_words:
        return 0.0
    # Base confidence from word count
    length_conf = sample_size_confidence(word_count, min_words, ideal_words)
    # Bonus: at least some hits exist (avoid confident 0-scores on long text)
    hit_boost = min(hits / 3, 1.0) * 0.2  # up to +0.2 for 3+ hits
    return round(min(length_conf + hit_boost, 1.0), 3)


# ── Outlier removal (IQR) ────────────────────────────────────────────────────

def remove_outliers_iqr(
    values: list[float],
    factor: float = 1.5,
) -> list[float]:
    """
    Remove outliers from a numeric list using the IQR method.

    Returns the filtered list with values outside
    [Q1 - factor*IQR, Q3 + factor*IQR] removed.

    If fewer than 4 values, returns the original list unchanged
    (IQR is unreliable with very small samples).
    """
    if len(values) < 4:
        return list(values)

    sorted_vals = sorted(values)
    n = len(sorted_vals)
    q1 = sorted_vals[n // 4]
    q3 = sorted_vals[(3 * n) // 4]
    iqr = q3 - q1

    lower = q1 - factor * iqr
    upper = q3 + factor * iqr

    return [v for v in values if lower <= v <= upper]


# ── Exponential moving average ────────────────────────────────────────────────

def ema_smooth(
    values: list[float],
    alpha: float = 0.3,
) -> list[float]:
    """
    Apply exponential moving average smoothing to a time series.

    alpha controls smoothing: 0.1 = very smooth, 0.9 = nearly raw.
    Default 0.3 balances responsiveness with noise reduction.

    Returns a list of the same length as input.
    """
    if not values:
        return []

    result = [values[0]]
    for v in values[1:]:
        result.append(alpha * v + (1 - alpha) * result[-1])
    return result


# ── Re-export for convenience ─────────────────────────────────────────────────

from app.ml.analysis.interfaces import score_to_level  # noqa: E402, F401
