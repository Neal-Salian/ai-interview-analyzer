"""
Leadership metric plugin — Enterprise Competency Framework.

Detects leadership indicators from transcript content and behavioral signals.

V3.0: Evidence-first evaluation. When structured evidence is available
(from the preprocessing pipeline), the plugin scores pre-extracted
leadership behaviours (e.g., ownership, delegation, mentoring).
Falls back to keyword-based analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with keyword-density confidence,
      minimum word-count guards, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
)
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    keyword_density_confidence,
    score_to_level,
    evidence_based_confidence,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class LeadershipMetric:
    name = "Leadership"
    description = (
        "Detects leadership indicators from the candidate's language, "
        "including initiative, decisiveness, ownership, and team-oriented framing."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    LEADERSHIP_KEYWORDS = [
        "led", "lead", "leading", "managed", "directed", "oversaw",
        "mentored", "coached", "delegated", "drove", "championed",
        "spearheaded", "initiated", "founded", "established",
        "influenced", "inspired", "motivated", "empowered",
        "orchestrated", "coordinated", "supervised",
    ]

    INITIATIVE_KEYWORDS = [
        "proposed", "suggested", "volunteered", "started", "launched",
        "created", "built", "introduced", "pioneered", "identified",
        "recognized", "took the initiative", "stepped up",
    ]

    DECISIVE_KEYWORDS = [
        "decided", "chose", "determined", "committed", "prioritized",
        "resolved", "concluded", "selected", "opted", "went with",
    ]

    # Minimum data thresholds
    MIN_TRANSCRIPT_WORDS = 100
    IDEAL_TRANSCRIPT_WORDS = 300
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            # Check for relevant behaviours
            rel_types = ["leadership", "ownership", "initiative", "decision_making", "accountability"]
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
        """Score leadership using pre-extracted behaviour evidence."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        # We will score based on frequency and confidence of leadership-related behaviours.
        # Max score is achieved with ~4-5 high-confidence behaviours.
        avg_confidence = sum(b.confidence for b in behaviours) / len(behaviours)
        base_score = min(int(len(behaviours) * 20 + avg_confidence * 20), 100)

        components.append(SignalComponent(
            score=max(0, min(100, base_score)),
            confidence=avg_confidence,
            signal_name="leadership_behaviours",
        ))

        # Track evidence
        for b in behaviours:
            evidence_ids.append(b.id)
            if b.transcript_reference:
                transcript_refs.append(b.transcript_reference)

        # ── Also include STAR signal if available ─────────────────────────
        if evidence.star_extractions:
            star_score = int(
                sum(s.completeness for s in evidence.star_extractions)
                / len(evidence.star_extractions) * 100
            )
            star_confidence = sum(
                s.confidence for s in evidence.star_extractions
            ) / len(evidence.star_extractions)

            components.append(SignalComponent(
                score=star_score,
                confidence=star_confidence,
                signal_name="star_structure",
            ))

        # ── Aggregate ─────────────────────────────────────────────────────
        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        # Build reasoning
        types_found = set(b.behaviour_type for b in behaviours)
        reasoning_parts = [
            f"Observed behaviours: {', '.join(types_found)}."
        ]
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Strong leadership indicators observed. Probe for scale of impact in follow-up."
            )
        else:
            recommendations.append(
                "Limited leadership indicators. If role requires leadership, ask for specific examples of driving outcomes."
            )

        return EnhancedMetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=[{"source": "evidence_pipeline", "count": len(behaviours)}],
            explanation=(
                f"Leadership assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"leadership capability based on {len(behaviours)} observations."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _keyword_based_compute(self, ctx: SessionContext) -> MetricResult:
        """V2 keyword-based fallback logic (unchanged for backward compatibility)."""
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        transcript = getattr(ctx, "candidate_transcript", "") or ctx.full_transcript
        if not transcript or not transcript.strip():
            return MetricResult(
                name=self.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                confidence_details=[],
                evidence=[],
                explanation="No transcript data available.",
                signals_used=[],
            )

        text_lower = transcript.lower()
        word_count = max(len(text_lower.split()), 1)

        # ── Signal 1: Leadership keywords ────────────────────────────────
        leadership_hits = sum(text_lower.count(kw) for kw in self.LEADERSHIP_KEYWORDS)
        sig_confidence = keyword_density_confidence(
            hits=leadership_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            leadership_density = (leadership_hits / word_count) * 100
            leadership_score = int(min(leadership_density * 20, 100))

            components.append(SignalComponent(
                score=max(0, min(100, leadership_score)),
                confidence=sig_confidence,
                signal_name="leadership_language",
            ))

            if leadership_hits > 0:
                evidence.append({
                    "quote": f"Used {leadership_hits} leadership-related term(s) across the interview",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 2: Initiative language ────────────────────────────────
        initiative_hits = sum(text_lower.count(kw) for kw in self.INITIATIVE_KEYWORDS)
        sig_confidence = keyword_density_confidence(
            hits=initiative_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            initiative_density = (initiative_hits / word_count) * 100
            initiative_score = int(min(initiative_density * 25, 100))

            components.append(SignalComponent(
                score=max(0, min(100, initiative_score)),
                confidence=sig_confidence,
                signal_name="initiative_language",
            ))

        # ── Signal 3: Decisive language ──────────────────────────────────
        decisive_hits = sum(text_lower.count(kw) for kw in self.DECISIVE_KEYWORDS)
        sig_confidence = keyword_density_confidence(
            hits=decisive_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            decisive_density = (decisive_hits / word_count) * 100
            decisive_score = int(min(decisive_density * 30, 100))

            components.append(SignalComponent(
                score=max(0, min(100, decisive_score)),
                confidence=sig_confidence,
                signal_name="decisiveness",
            ))

        # ── Signal 4: Confident delivery ─────────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                positive_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in {"happy", "surprise"}
                )
                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                composed_ratio = (positive_count + neutral_count) / n
                delivery_score = int(composed_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, delivery_score)),
                    confidence=sig_confidence,
                    signal_name="confident_delivery",
                ))

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
                explanation="Insufficient data to assess leadership.",
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
                f"Leadership assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(LeadershipMetric())
