"""
Communication effectiveness metric plugin — Enterprise Competency Framework.

Evaluates communication competency based on structured evidence:
  - clarity, articulation, structure, persuasion, listening, speaking_confidence

V3.0: Evidence-first evaluation.  When structured evidence is available
(from the preprocessing pipeline), the plugin scores pre-extracted
communication observations.  Falls back to keyword-based analysis when
evidence is unavailable (backward compatibility).

v2.0: Confidence-weighted scoring with sample-size guards, keyword-density
      confidence, and per-signal confidence breakdown.
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


class CommunicationMetric:
    name = "Communication"
    description = (
        "Evaluates communication effectiveness including clarity, articulation, "
        "structure, persuasion, listening, and speaking confidence."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"communication_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    STAR_KEYWORDS = {
        "situation": ["situation", "context", "background", "scenario", "when"],
        "task": ["task", "goal", "objective", "challenge", "needed to", "had to", "responsible"],
        "action": ["action", "decided", "implemented", "built", "created", "designed", "led", "developed"],
        "result": ["result", "outcome", "achieved", "improved", "reduced", "increased", "delivered", "impact"],
    }

    # Minimum data thresholds
    MIN_TRANSCRIPT_WORDS = 50
    IDEAL_TRANSCRIPT_WORDS = 200
    MIN_TRANSCRIPT_CHUNKS = 3
    IDEAL_TRANSCRIPT_CHUNKS = 15
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty() and evidence.communication:
            return self._evidence_based_compute(ctx, evidence)

        # ── Fallback: keyword-based evaluation (V2 logic) ────────────────
        return self._keyword_based_compute(ctx)

    def _evidence_based_compute(
        self, ctx: SessionContext, evidence
    ) -> EnhancedMetricResult:
        """Score communication using pre-extracted evidence objects."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        # ── Score each communication dimension ────────────────────────────
        for dimension in ["clarity", "articulation", "structure",
                          "persuasion", "listening", "speaking_confidence"]:
            dim_evidence = evidence.get_communication_by_dimension(dimension)
            if not dim_evidence:
                continue

            # Average confidence across evidence items for this dimension
            avg_conf = sum(e.confidence for e in dim_evidence) / len(dim_evidence)

            # Score based on the assessment quality
            dim_score = int(avg_conf * 80 + 20)  # 20-100 range based on confidence

            components.append(SignalComponent(
                score=max(0, min(100, dim_score)),
                confidence=avg_conf,
                signal_name=f"communication_{dimension}",
            ))

            for e in dim_evidence:
                evidence_ids.append(e.id)
                if e.transcript_reference:
                    transcript_refs.append(e.transcript_reference)

            sub_dimensions.append({
                "dimension": dimension,
                "score": dim_score,
                "confidence": round(avg_conf, 3),
                "evidence_count": len(dim_evidence),
                "assessment": dim_evidence[0].assessment if dim_evidence else "",
            })

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
        if not components:
            return self._keyword_based_compute(ctx)

        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        # Build reasoning
        strong_dims = [d["dimension"] for d in sub_dimensions if d["score"] >= 70]
        weak_dims = [d["dimension"] for d in sub_dimensions if d["score"] < 50]

        reasoning_parts = []
        if strong_dims:
            reasoning_parts.append(
                f"Strong performance in: {', '.join(strong_dims)}."
            )
        if weak_dims:
            reasoning_parts.append(
                f"Areas for improvement: {', '.join(weak_dims)}."
            )
        reasoning_parts.append(
            f"Assessment based on {len(evidence.communication)} "
            f"communication observations."
        )

        recommendations = []
        if weak_dims:
            recommendations.append(
                f"Consider probing deeper into {', '.join(weak_dims)} "
                f"in follow-up interviews."
            )
        if result["final_score"] >= 80:
            recommendations.append(
                "Strong communicator — suitable for client-facing roles."
            )

        return EnhancedMetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=[{"source": "evidence_pipeline", "count": len(evidence.communication)}],
            explanation=(
                f"Communication assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"communication effectiveness."
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

        words = transcript.lower().split()
        word_count = max(len(words), 1)

        # ── Signal 1: Vocabulary diversity ───────────────────────────────
        vocab_confidence = sample_size_confidence(
            word_count, self.MIN_TRANSCRIPT_WORDS, self.IDEAL_TRANSCRIPT_WORDS
        )
        if vocab_confidence > 0:
            unique_words = set(words)
            diversity_ratio = len(unique_words) / word_count
            diversity_score = int(min(diversity_ratio * 200, 100))

            components.append(SignalComponent(
                score=max(0, min(100, diversity_score)),
                confidence=vocab_confidence,
                signal_name="vocabulary_diversity",
            ))

            if diversity_ratio < 0.25:
                evidence.append({
                    "quote": f"Vocabulary diversity ratio: {diversity_ratio:.2f} (limited word variety)",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 2: Response coherence (words per chunk) ───────────────
        if ctx.transcripts:
            n = len(ctx.transcripts)
            chunk_confidence = sample_size_confidence(
                n, self.MIN_TRANSCRIPT_CHUNKS, self.IDEAL_TRANSCRIPT_CHUNKS
            )
            if chunk_confidence > 0:
                chunk_word_counts = [
                    len(t.get("text", "").split()) for t in ctx.transcripts
                    if t.get("text", "").strip()
                ]
                if chunk_word_counts:
                    avg_words = sum(chunk_word_counts) / len(chunk_word_counts)
                    if avg_words < 10:
                        coherence_score = int(avg_words * 5)
                    elif avg_words <= 50:
                        coherence_score = int(min(avg_words * 2, 100))
                    else:
                        coherence_score = int(max(100 - (avg_words - 50), 40))

                    components.append(SignalComponent(
                        score=max(0, min(100, coherence_score)),
                        confidence=chunk_confidence,
                        signal_name="response_coherence",
                    ))

        # ── Signal 3: STAR structure ─────────────────────────────────────
        text_lower = transcript.lower()
        total_star_hits = 0
        star_hits = {}
        for component_name, keywords in self.STAR_KEYWORDS.items():
            hits = sum(text_lower.count(kw) for kw in keywords)
            star_hits[component_name] = hits
            total_star_hits += hits

        components_present = sum(1 for v in star_hits.values() if v > 0)
        star_confidence = keyword_density_confidence(
            hits=total_star_hits,
            word_count=word_count,
            min_words=100,
            ideal_words=300,
        )
        if star_confidence > 0:
            star_score = int((components_present / 4) * 100)

            components.append(SignalComponent(
                score=star_score,
                confidence=star_confidence,
                signal_name="star_structure",
            ))

            if components_present >= 3:
                evidence.append({
                    "quote": f"Candidate used {components_present}/4 STAR framework components in responses",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 4: Sentiment consistency ──────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            tone_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if tone_confidence > 0:
                positive_emotions = {"happy", "surprise"}
                positive_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in positive_emotions
                )
                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                stable_ratio = (positive_count + neutral_count) / n
                tone_score = int(stable_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, tone_score)),
                    confidence=tone_confidence,
                    signal_name="communication_tone",
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
                explanation="Insufficient data to assess communication.",
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
                f"Communication assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(CommunicationMetric())
