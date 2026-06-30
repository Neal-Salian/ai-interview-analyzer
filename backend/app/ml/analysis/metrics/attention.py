"""
Attention metric plugin — Enterprise Competency Framework.

Assesses how attentive and focused the candidate was during the interview.

V3.0: Evidence-first evaluation. Integrates structured evidence (from the
preprocessing pipeline) with physiological signals (attention events).
Falls back to pure physiological analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with sample-size guards,
      proportional proxy weighting, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
)
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    score_to_level,
    evidence_based_confidence,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class AttentionMetric:
    name = "Attention"
    description = (
        "Measures candidate focus and attentiveness based on gaze patterns, "
        "face visibility, and attention consistency throughout the interview."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    # Minimum data thresholds
    MIN_ATTENTION_EVENTS = 5
    IDEAL_ATTENTION_EVENTS = 30
    MIN_CONSISTENCY_EVENTS = 10
    IDEAL_CONSISTENCY_EVENTS = 50
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            rel_types = ["attentiveness", "focus", "active_listening"]
            behaviours = []
            for t in rel_types:
                behaviours.extend(evidence.get_behaviours_by_type(t))
            
            if behaviours:
                return self._evidence_based_compute(ctx, evidence, behaviours)

        # ── Fallback: keyword-based evaluation (V2 logic) ────────────────
        return self._keyword_based_compute(ctx)

    def _evidence_based_compute(
        self, ctx: SessionContext, evidence, behaviours
    ) -> EnhancedMetricResult:
        """Score attention using pre-extracted behaviour evidence combined with raw physiological signals."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        avg_confidence = sum(b.confidence for b in behaviours) / len(behaviours)
        base_score = min(int(len(behaviours) * 20 + avg_confidence * 20), 100)

        components.append(SignalComponent(
            score=max(0, min(100, base_score)),
            confidence=avg_confidence,
            signal_name="attentiveness_behaviours",
        ))

        # Track evidence
        for b in behaviours:
            evidence_ids.append(b.id)
            if b.transcript_reference:
                transcript_refs.append(b.transcript_reference)

        # 2. Add physiological signals if available
        phys_components, phys_evidence = self._get_physiological_signals(ctx)
        components.extend(phys_components)

        # ── Aggregate ─────────────────────────────────────────────────────
        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        reasoning_parts = []
        if phys_components:
            reasoning_parts.append(
                f"Combined verbal attentiveness analysis with physiological attention signals "
                f"({len(phys_components)} sensor metrics used)."
            )
        else:
            reasoning_parts.append(
                "Assessed based on transcript-level attentiveness (physiological data unavailable)."
            )
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Strong focus and attention. Highly attentive presence."
            )
        else:
            recommendations.append(
                "Observed distractions or lack of focus. Consider remote environment factors."
            )

        return EnhancedMetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=[{"source": "evidence_pipeline", "count": len(behaviours)}] + phys_evidence,
            explanation=(
                f"Attention assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"focus and attentiveness."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _get_physiological_signals(self, ctx: SessionContext) -> tuple[list[SignalComponent], list[dict]]:
        """Extract physiological attention signals (used in both V2 and V3)."""
        components = []
        evidence = []

        # ── Signal 1: Eye contact ratio ──────────────────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                center = sum(
                    1 for a in ctx.attention_events
                    if a.get("direction") == "center"
                )
                center_ratio = center / n
                eye_score = int(center_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, eye_score)),
                    confidence=sig_confidence,
                    signal_name="eye_contact_ratio",
                ))

                evidence.append({
                    "quote": f"Direct eye contact maintained {center_ratio:.0%} of the time ({center}/{n} frames)",
                    "timestamp": "",
                    "source": "attention_tracking",
                })

        # ── Signal 2: Face-missing frequency ─────────────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                missing = sum(
                    1 for a in ctx.attention_events
                    if a.get("direction") == "missing"
                )
                missing_ratio = missing / n
                presence_score = int(max(0, (1 - missing_ratio * 3.3)) * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, presence_score)),
                    confidence=sig_confidence,
                    signal_name="face_visibility",
                ))

                if missing_ratio > 0.1:
                    evidence.append({
                        "quote": f"Face was not visible in {missing_ratio:.0%} of frames",
                        "timestamp": "",
                        "source": "attention_tracking",
                    })

        # ── Signal 3: Attention consistency over time ────────────────────
        if ctx.attention_events and len(ctx.attention_events) >= self.MIN_CONSISTENCY_EVENTS:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_CONSISTENCY_EVENTS, self.IDEAL_CONSISTENCY_EVENTS
            )

            mid = n // 2
            first_half = ctx.attention_events[:mid]
            second_half = ctx.attention_events[mid:]

            first_center = sum(
                1 for a in first_half if a.get("direction") == "center"
            ) / max(len(first_half), 1)
            second_center = sum(
                1 for a in second_half if a.get("direction") == "center"
            ) / max(len(second_half), 1)

            drop = first_center - second_center
            if drop > 0.2:
                consistency_score = int((1 - drop) * 100)
                evidence.append({
                    "quote": f"Eye contact dropped from {first_center:.0%} to {second_center:.0%} in the second half",
                    "timestamp": "",
                    "source": "attention_tracking",
                })
            else:
                consistency_score = 80

            components.append(SignalComponent(
                score=max(0, min(100, consistency_score)),
                confidence=sig_confidence,
                signal_name="attention_consistency",
            ))

        # ── Fallback: Use emotion data if no attention data ──────────────
        if not ctx.attention_events and ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                proxy_confidence = min(sig_confidence, 0.4)

                neutral_ratio = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                ) / max(n, 1)
                proxy_score = int((1 - max(0, neutral_ratio - 0.5) * 2) * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, proxy_score)),
                    confidence=proxy_confidence,
                    signal_name="emotion_engagement_proxy",
                ))
                evidence.append({
                    "quote": "Attention estimated from emotion data (no gaze tracking available)",
                    "timestamp": "",
                    "source": "emotion_detection",
                })

        return components, evidence

    def _keyword_based_compute(self, ctx: SessionContext) -> MetricResult:
        """V2 keyword-based fallback logic."""
        components, evidence = self._get_physiological_signals(ctx)

        # ── Aggregate ────────────────────────────────────────────────────
        if not components:
            return MetricResult(
                name=self.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                confidence_details=[],
                evidence=[],
                explanation="Insufficient data to assess attention.",
                signals_used=[],
            )

        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        return MetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=evidence,
            explanation=(
                f"Attention assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(AttentionMetric())
