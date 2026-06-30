"""
Metric aggregator — Enterprise Competency Framework.

Orchestrates the full analysis pipeline:
  1. Run evidence preprocessing (single LLM call)
  2. Load tenant-specific configuration (weights, enabled metrics)
  3. Execute core plugins → tenant plugins (dependency-ordered)
  4. Auto-normalize V1 MetricResult → V2 EnhancedMetricResult
  5. Apply weighted aggregation
  6. Run work-style inference (optional layer)
  7. Produce recruiter-ready output

Called during session teardown or on-demand via API.
Each metric runs in its own try/except so a single failure never crashes
the entire pipeline.
"""

import logging
from typing import Any
from sqlalchemy.orm import Session as DBSession

from .interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
    ReadonlySessionContext,
    normalize_to_enhanced,
)
from .registry import (
    get_enabled_metrics,
    discover_metrics,
    discover_tenant_metrics,
    load_weights_config,
    load_competency_config,
)

logger = logging.getLogger(__name__)


def run_all_metrics(ctx: SessionContext) -> dict:
    """
    Execute the full Enterprise Competency Framework pipeline.

    1. Run evidence preprocessing (if not already done)
    2. Load tenant-specific configs
    3. Execute all enabled metrics (core + tenant)
    4. Normalize results, apply weights, aggregate
    5. Optionally run work-style inference
    6. Return structured output for session_summary JSONB

    Each metric runs independently — one failure does not affect others.
    """
    discover_metrics()  # ensure all core modules are imported

    # ── Load tenant config if company_id is set ───────────────────────────
    company_id = ctx.company_id
    if company_id:
        discover_tenant_metrics(company_id)

    weights = load_weights_config(company_id)
    competency_config = load_competency_config(company_id)
    ctx.competency_config = competency_config

    # ── Run evidence preprocessing (if not already done) ──────────────────
    if ctx.evidence is None:
        _run_preprocessing(ctx)

    # ── Get enabled metrics (core + tenant, dependency-sorted) ────────────
    enabled = get_enabled_metrics(company_id)

    logger.info(
        f"[aggregator] Running {len(enabled)} metric(s) "
        f"for session {ctx.session_id}"
        f"{f' (company={company_id})' if company_id else ''}"
    )

    # ── Execute plugins ───────────────────────────────────────────────────
    results: list[EnhancedMetricResult] = []

    for metric in enabled:
        try:
            # Tenant plugins get ReadonlySessionContext
            is_tenant = hasattr(metric, "plugin_metadata") and \
                metric.plugin_metadata.get("tier") == "tenant"

            if is_tenant:
                metric_ctx = ReadonlySessionContext(ctx)
            else:
                metric_ctx = ctx

            raw_result: MetricResult = metric.compute(metric_ctx)

            # Auto-normalize V1 → V2
            enhanced = normalize_to_enhanced(raw_result)
            results.append(enhanced)

            logger.debug(
                f"[aggregator] {metric.name}: "
                f"{enhanced.score}/100 ({enhanced.level}) "
                f"[confidence={enhanced.confidence:.2f}]"
            )
        except Exception as e:
            logger.warning(
                f"[aggregator] Metric '{metric.name}' failed: {e}",
                exc_info=True,
            )
            # Graceful fallback — don't crash the pipeline
            results.append(EnhancedMetricResult(
                name=metric.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                explanation=f"Metric computation failed: {e}",
                summary=f"Metric computation failed: {e}",
                metadata={"error": str(e)},
            ))

    # ── Apply weighted aggregation ────────────────────────────────────────
    result_dicts = []
    for r in results:
        d = r.to_dict()
        key = r.name.lower().replace(" ", "_")
        d["weight"] = weights.get(key, 1.0)
        result_dicts.append(d)

    # ── Compute overall confidence ────────────────────────────────────────
    valid_results = [
        r for r in results if r.level != "Unavailable"
    ]
    confidences = [r.confidence for r in valid_results]
    overall_confidence = (
        round(sum(confidences) / len(confidences), 3)
        if confidences else 0.0
    )

    # ── Compute weighted overall score ────────────────────────────────────
    weighted_score = _compute_weighted_score(valid_results, weights)

    # ── Aggregate evidence ────────────────────────────────────────────────
    all_recommendations = []
    all_evidence_ids = []
    for r in valid_results:
        all_recommendations.extend(r.recommendations)
        all_evidence_ids.extend(r.evidence_ids)

    # ── Data quality summary ──────────────────────────────────────────────
    word_count = len(ctx.full_transcript.split()) if ctx.full_transcript else 0
    evidence_count = 0
    if ctx.evidence and not ctx.evidence.is_empty():
        evidence_count = len(ctx.evidence.all_evidence_ids)

    data_quality = {
        "emotion_frames": len(ctx.emotions),
        "transcript_words": word_count,
        "transcript_chunks": len(ctx.transcripts),
        "attention_events": len(ctx.attention_events),
        "integrity_events": len(ctx.integrity_events),
        "duration_minutes": ctx.duration_minutes,
        "evidence_items_extracted": evidence_count,
        "signals_quality": _classify_data_quality(
            emotion_frames=len(ctx.emotions),
            transcript_words=word_count,
            attention_events=len(ctx.attention_events),
        ),
    }

    # ── Evidence summary ──────────────────────────────────────────────────
    evidence_summary = {}
    if ctx.evidence and not ctx.evidence.is_empty():
        evidence_summary = ctx.evidence.to_dict()

    # ── Work-style inference (optional — never affects scores) ────────────
    work_style_insights = _run_work_style_inference(valid_results)

    logger.info(
        f"[aggregator] Completed: {len(results)} metric(s) computed "
        f"for session {ctx.session_id} "
        f"[overall_confidence={overall_confidence}, "
        f"weighted_score={weighted_score}]"
    )

    return {
        "metrics": result_dicts,
        "overall_confidence": overall_confidence,
        "weighted_overall_score": weighted_score,
        "data_quality": data_quality,
        "evidence_summary": evidence_summary,
        "aggregated_recommendations": list(set(all_recommendations)),
        "work_style_insights": work_style_insights,
        "framework_version": "enterprise_competency_v2",
    }


def _run_preprocessing(ctx: SessionContext) -> None:
    """Run evidence preprocessing if not already done."""
    try:
        from app.ml.analysis.preprocessing import _run_evidence_extraction
        _run_evidence_extraction(ctx)
    except Exception as e:
        logger.warning(
            f"[aggregator] Preprocessing failed: {e} — "
            f"plugins will use fallback scoring"
        )
        from app.ml.analysis.evidence_types import EvidenceCollection
        ctx.evidence = EvidenceCollection()


def _compute_weighted_score(
    results: list[EnhancedMetricResult],
    weights: dict[str, float],
) -> int:
    """
    Compute a weighted overall score from all valid metric results.

    If no weights are configured, uses equal weighting.
    """
    if not results:
        return 0

    total_weight = 0.0
    weighted_sum = 0.0

    for r in results:
        key = r.name.lower().replace(" ", "_")
        w = weights.get(key, 1.0)
        weighted_sum += r.score * w
        total_weight += w

    if total_weight <= 0:
        return 0

    return max(0, min(100, int(weighted_sum / total_weight)))


def _run_work_style_inference(
    results: list[EnhancedMetricResult],
) -> list[dict]:
    """
    Optional work-style inference layer.

    Combines competency scores into work-style insights.
    This NEVER modifies competency scores — it's a one-way
    interpretation layer.

    Returns list of work-style insight dicts.
    """
    try:
        from app.ml.analysis.work_style import infer_work_styles
        return infer_work_styles(results)
    except ImportError:
        logger.debug("[aggregator] work_style module not available — skipping")
        return []
    except Exception as e:
        logger.warning(f"[aggregator] Work-style inference failed: {e}")
        return []


def _classify_data_quality(
    emotion_frames: int,
    transcript_words: int,
    attention_events: int,
) -> str:
    """
    Classify overall data quality as high/medium/low.

    Used by the report to display a data quality badge.
    """
    score = 0
    if emotion_frames >= 50:
        score += 2
    elif emotion_frames >= 10:
        score += 1
    if transcript_words >= 200:
        score += 2
    elif transcript_words >= 50:
        score += 1
    if attention_events >= 30:
        score += 2
    elif attention_events >= 5:
        score += 1

    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"
