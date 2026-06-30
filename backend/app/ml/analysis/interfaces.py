"""
Metric framework interfaces — Enterprise Competency Framework.

Defines the standardized contracts for the metric plugin system:

  V1 (legacy):  MetricResult   + BaseMetric        — unchanged, backward compatible
  V2 (enhanced): EnhancedMetricResult + EnhancedMetric — evidence-first competency evaluation

Adding a new metric requires only:
  1. Create a file in app/ml/analysis/metrics/
  2. Implement a class satisfying BaseMetric (or EnhancedMetric for V2)
  3. Call register_metric() at module level

The aggregator auto-normalizes V1 results into V2 format so legacy plugins
continue working without modification.
"""

from __future__ import annotations

import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

logger = logging.getLogger(__name__)


# ── Plugin engine version ─────────────────────────────────────────────────────
# Plugins declare which engine version they target so we can detect
# compatibility mismatches during registration.

PLUGIN_ENGINE_VERSION = 2


# ── V1: Legacy result (unchanged) ────────────────────────────────────────────


@dataclass
class MetricResult:
    """
    V1 standardized result that every metric must return from compute().

    This class is frozen — do NOT modify it.  All existing plugins depend
    on this exact shape.  V2 extends it via EnhancedMetricResult.

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


# ── V2: Enhanced result for Enterprise Competency Framework ──────────────────


@dataclass
class EnhancedMetricResult(MetricResult):
    """
    V2 evidence-first result for competency evaluation plugins.

    Extends MetricResult with:
        summary:               Brief human-readable finding (not a score)
        reasoning:             Detailed explanation of how the assessment was derived
        recommendations:       Actionable recruiter recommendations
        transcript_references: Exact transcript excerpts supporting the assessment
        evidence_ids:          References to EvidenceItem IDs (avoids duplication)
        sub_dimensions:        Per-dimension breakdown (e.g. clarity, articulation)
        metadata:              Plugin-specific metadata (version, engine, etc.)

    Internally, plugins work with assessments and findings.
    The 'score' field is populated for recruiter-facing reports.
    """
    summary: str = ""
    reasoning: str = ""
    recommendations: list[str] = field(default_factory=list)
    transcript_references: list[str] = field(default_factory=list)
    evidence_ids: list[str] = field(default_factory=list)
    sub_dimensions: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["summary"] = self.summary
        base["reasoning"] = self.reasoning
        base["recommendations"] = self.recommendations
        base["transcript_references"] = self.transcript_references
        base["evidence_ids"] = self.evidence_ids
        base["sub_dimensions"] = self.sub_dimensions
        base["metadata"] = self.metadata
        base["result_version"] = 2
        return base


def normalize_to_enhanced(result: MetricResult) -> EnhancedMetricResult:
    """
    Normalize a V1 MetricResult into a V2 EnhancedMetricResult.

    Used by the aggregator to ensure all results have the same shape
    regardless of whether a plugin returns V1 or V2.
    Legacy plugins continue working without modification.
    """
    if isinstance(result, EnhancedMetricResult):
        return result

    return EnhancedMetricResult(
        name=result.name,
        score=result.score,
        raw_score=result.raw_score,
        level=result.level,
        confidence=result.confidence,
        confidence_details=result.confidence_details,
        evidence=result.evidence,
        explanation=result.explanation,
        signals_used=result.signals_used,
        summary=result.explanation,  # map explanation → summary for V1
        reasoning=result.explanation,
        recommendations=[],
        transcript_references=[],
        evidence_ids=[],
        sub_dimensions=[],
        metadata={"result_version": 1, "normalized": True},
    )


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
    Data bag populated by the aggregator and preprocessing pipeline before
    metrics run.  Every metric receives the same context.

    Constructed from DB queries at analysis time (teardown or on-demand),
    then enriched by the evidence pipeline with STAR extractions,
    behaviour evidence, communication analysis, and technical evidence.
    """
    session_id: str = ""
    candidate_name: str = ""
    job_title: str = ""
    job_skills: list[str] = field(default_factory=list)
    duration_minutes: float | None = None

    # ── Raw data from the session ─────────────────────────────────────────
    emotions: list[dict] = field(default_factory=list)
    transcripts: list[dict] = field(default_factory=list)
    full_transcript: str = ""

    # ── Candidate Attribution ─────────────────────────────────────────────
    candidate_transcript: str = ""
    recruiter_transcript: str = ""
    conversation_timeline: list[dict] = field(default_factory=list)
    candidate_segments: list[dict] = field(default_factory=list)
    recruiter_segments: list[dict] = field(default_factory=list)

    # ── Attention tracking data ───────────────────────────────────────────
    attention_events: list[dict] = field(default_factory=list)

    # ── Integrity data ────────────────────────────────────────────────────
    integrity_events: list[dict] = field(default_factory=list)

    # ── Questions data ────────────────────────────────────────────────────
    questions: list[dict] = field(default_factory=list)

    # ── Enterprise Competency Framework: Evidence Pipeline outputs ────────
    # These are populated by preprocessing.py BEFORE plugins execute.
    # Plugins consume these — they never call the LLM independently.

    evidence: Any = None          # EvidenceCollection from evidence_types.py
    company_id: str | None = None # Active tenant ID for config resolution

    # ── Competency configuration (loaded from YAML) ──────────────────────
    competency_config: dict[str, Any] = field(default_factory=dict)


class ReadonlySessionContext:
    """
    Immutable wrapper around SessionContext for tenant plugin sandboxing.

    Tenant plugins receive this instead of the raw SessionContext.
    All attribute access is proxied read-only — mutations raise AttributeError.
    The evidence collection is deep-copied to prevent any shared-state bugs.

    Company plugins:
      - CAN read any field
      - CANNOT modify any field
      - CANNOT access the database
      - CANNOT access other tenants' data
    """

    __slots__ = ("_ctx",)

    def __init__(self, ctx: SessionContext) -> None:
        # Deep-copy to guarantee tenant plugins can't mutate shared state
        object.__setattr__(self, "_ctx", copy.deepcopy(ctx))

    def __getattr__(self, name: str) -> Any:
        return getattr(object.__getattribute__(self, "_ctx"), name)

    def __setattr__(self, name: str, value: Any) -> None:
        raise AttributeError(
            f"ReadonlySessionContext is immutable — cannot set '{name}'. "
            f"Tenant plugins must not modify the session context."
        )

    def __delattr__(self, name: str) -> None:
        raise AttributeError(
            f"ReadonlySessionContext is immutable — cannot delete '{name}'."
        )


# ── V1: Legacy protocol (unchanged) ──────────────────────────────────────────


@runtime_checkable
class BaseMetric(Protocol):
    """
    V1 protocol that every metric plugin must satisfy.

    Using Protocol (structural subtyping) instead of ABC so metric classes
    don't need to inherit from anything — they just need to have the right
    attributes and methods. This follows the existing codebase's duck-typing
    patterns.

    This protocol is FROZEN — do not modify it.
    """
    name: str
    description: str
    version: str

    def compute(self, ctx: SessionContext) -> MetricResult:
        """Run the metric on the given session context and return a result."""
        ...


# ── V2: Enhanced protocol for Enterprise Competency Framework ────────────────


@runtime_checkable
class EnhancedMetric(Protocol):
    """
    V2 protocol for evidence-first competency evaluation plugins.

    Extends the BaseMetric contract with:
      - requires:             versioned preprocessing dependencies
      - author:               plugin author / maintainer
      - supported_engine:     minimum PLUGIN_ENGINE_VERSION supported
      - plugin_metadata:      additional metadata for enterprise plugin management

    Plugins declare their preprocessing requirements so the registry can
    validate that required evidence is available before execution.

    Example:
        class LeadershipMetric:
            name = "Leadership"
            description = "Evaluates leadership competencies..."
            version = "3.0"
            author = "Platform Team"
            supported_engine = 2
            requires = {"star": 1, "behaviour_evidence": 1}
            plugin_metadata = {"category": "competency", "tier": "core"}
    """
    name: str
    description: str
    version: str
    author: str
    supported_engine: int
    requires: dict[str, int]     # {"capability_name": minimum_version}
    plugin_metadata: dict[str, Any]

    def compute(self, ctx: SessionContext) -> EnhancedMetricResult:
        """Run the competency evaluation and return an evidence-first result."""
        ...
