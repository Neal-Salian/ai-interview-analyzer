"""
Metric framework interfaces.

Defines the standardized contract that every metric plugin must follow,
the SessionContext data bag passed to metrics, and the MetricResult
dataclass returned by every metric.

Adding a new metric requires only:
  1. Create a file in app/ml/analysis/metrics/
  2. Implement a class satisfying BaseMetric (name, description, version, compute)
  3. Call register_metric() at module level
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ── Standardized result every metric must return ─────────────────────────────


@dataclass
class MetricResult:
    """
    Standardized result that every metric must return from compute().

    Fields:
        name:                Human-readable metric name (e.g. "Confidence")
        score:               0–100 integer score (confidence-weighted)
        raw_score:           0–100 integer score (unweighted average, for auditing)
        level:               Human-readable level (e.g. "Strong")
        confidence:          0.0–1.0 float indicating assessment reliability
        confidence_details:  Per-signal breakdown: [{signal, score, confidence, weight_applied}]
        evidence:            List of supporting evidence dicts
        explanation:         Human-readable explanation of the score
        signals_used:        List of signal names that contributed to the score
    """
    name: str
    score: int
    level: str
    confidence: float
    raw_score: int = 0
    confidence_details: list[dict] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    explanation: str = ""
    signals_used: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "score": self.score,
            "raw_score": self.raw_score,
            "level": self.level,
            "confidence": round(self.confidence, 3),
            "confidence_details": self.confidence_details,
            "evidence": self.evidence,
            "explanation": self.explanation,
            "signals_used": self.signals_used,
        }


def score_to_level(score: int) -> str:
    """
    Consistent score → level mapping used by all metrics.
    Keeps level labels uniform across the entire system.
    """
    if score >= 80:
        return "Very Strong"
    if score >= 60:
        return "Strong"
    if score >= 40:
        return "Moderate"
    if score >= 20:
        return "Weak"
    return "Very Weak"


# ── Read-only context passed to every metric ─────────────────────────────────


@dataclass
class SessionContext:
    """
    Read-only data bag populated by the aggregator before metrics run.
    Every metric receives the same context — they pick the signals they need.

    This is constructed from DB queries at analysis time (teardown or on-demand).
    """
    session_id: str = ""
    candidate_name: str = ""
    job_title: str = ""
    job_skills: list[str] = field(default_factory=list)
    duration_minutes: float | None = None

    # Raw data from the session
    emotions: list[dict] = field(default_factory=list)
    transcripts: list[dict] = field(default_factory=list)
    full_transcript: str = ""

    # Phase 2 — Attention tracking data
    attention_events: list[dict] = field(default_factory=list)

    # Phase 3 — Integrity data
    integrity_events: list[dict] = field(default_factory=list)

    # Questions data
    questions: list[dict] = field(default_factory=list)


# ── Protocol that every metric plugin must satisfy ───────────────────────────


@runtime_checkable
class BaseMetric(Protocol):
    """
    Protocol that every metric plugin must satisfy.

    Using Protocol (structural subtyping) instead of ABC so metric classes
    don't need to inherit from anything — they just need to have the right
    attributes and methods. This follows the existing codebase's duck-typing
    patterns.
    """
    name: str
    description: str
    version: str

    def compute(self, ctx: SessionContext) -> MetricResult:
        """Run the metric on the given session context and return a result."""
        ...
