"""
Engagement metric plugin — Enterprise Competency Framework.

Assesses candidate engagement based on:
  - Eye contact percentage (attention data)
  - Emotional expressiveness (emotion variety vs. flat neutral)
  - Response depth
  - Structured communication evidence (active listening, engagement)

V3.0: Evidence-first evaluation. Integrates structured evidence (from the
preprocessing pipeline) with physiological signals (emotions, attention).
Falls back to pure physiological analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with sample-size guards and
      per-signal confidence breakdown.
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


class EngagementMetric:
    name = "Engagement"
    description = (
        "Measures how actively the candidate participates in the interview "
        "through eye contact, emotional expressiveness, active listening, and response depth."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"communication_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    # Minimum data thresholds
    MIN_ATTENTION_EVENTS = 5
    IDEAL_ATTENTION_EVENTS = 30
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50
    MIN_TRANSCRIPT_CHUNKS = 3
    IDEAL_TRANSCRIPT_CHUNKS = 15
    MIN_QUESTIONS = 3
    IDEAL_QUESTIONS = 8

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            comm_evidence = evidence.get_communication_by_dimension("listening")
            behaviours = evidence.get_behaviours_by_type("engagement")
            
            if comm_evidence or behaviours:
                return self._evidence_based_compute(ctx, comm_evidence, behaviours)

        # ── Fallback: keyword-based evaluation (V2 logic) ────────────────
        return self._keyword_based_compute(ctx)

    def _evidence_based_compute(
        self, ctx: SessionContext, comm_evidence, behaviours
    ) -> EnhancedMetricResult:
        """Score engagement using pre-extracted evidence combined with raw signals."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        all_evidence = comm_evidence + behaviours
        if all_evidence:
            avg_confidence = sum(e.confidence for e in all_evidence) / len(all_evidence)
            base_score = int(avg_confidence * 80 + 20)
            
            components.append(SignalComponent(
                score=max(0, min(100, base_score)),
                confidence=avg_confidence,
                signal_name="active_listening_and_engagement",
            ))

            for e in all_evidence:
                evidence_ids.append(e.id)
                if getattr(e, "transcript_reference", None):
                    transcript_refs.append(e.transcript_reference)

        # 2. Add physiological signals if available
        phys_components, phys_evidence = self._get_physiological_signals(ctx)
        components.extend(phys_components)

        # ── Aggregate ─────────────────────────────────────────────────────
        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        reasoning_parts = []
        if phys_components:
            reasoning_parts.append(
                f"Combined verbal engagement analysis with physiological signals "
                f"({len(phys_components)} sensor metrics used)."
            )
        else:
            reasoning_parts.append(
                "Assessed based on transcript-level verbal engagement (physiological data unavailable)."
            )
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Candidate showed strong interview engagement. Likely to be highly participatory in team settings."
            )
        else:
            recommendations.append(
                "Engagement levels were lower than average. Consider whether remote work environment affected participation."
            )

        return EnhancedMetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=[{"source": "evidence_pipeline", "count": len(all_evidence)}] + phys_evidence,
            explanation=(
                f"Engagement assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"interview engagement."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _get_physiological_signals(self, ctx: SessionContext) -> tuple[list[SignalComponent], list[dict]]:
        """Extract emotion and attention signals (used in both V2 and V3)."""
        components = []
        evidence = []

        # ── Signal: Eye contact (attention data) ───────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                total = n
                center = sum(
                    1 for a in ctx.attention_events
                    if a.get("direction") == "center"
                )
                missing = sum(
                    1 for a in ctx.attention_events
                    if a.get("direction") == "missing"
                )
                engaged_ratio = center / total
                missing_ratio = missing / total
                eye_score = int(engaged_ratio * 100)
                if missing_ratio > 0.1:
                    eye_score = int(eye_score * (1 - missing_ratio))

                components.append(SignalComponent(
                    score=max(0, min(100, eye_score)),
                    confidence=sig_confidence,
                    signal_name="eye_contact_ratio",
                ))

                if engaged_ratio < 0.5:
                    evidence.append({
                        "quote": f"Candidate maintained direct eye contact {engaged_ratio:.0%} of the time",
                        "timestamp": "",
                        "source": "attention_tracking",
                    })

        # ── Signal: Emotional expressiveness ───────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                unique_emotions = set(
                    e.get("dominant_emotion") for e in ctx.emotions
                )
                raw_variety = min(len(unique_emotions) * 20, 100)
                variety_score = int(raw_variety * min(n / 20, 1.0))

                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                neutral_ratio = neutral_count / n
                expression_score = int(
                    variety_score * 0.4 + (1 - neutral_ratio) * 100 * 0.6
                )

                components.append(SignalComponent(
                    score=max(0, min(100, expression_score)),
                    confidence=sig_confidence,
                    signal_name="emotional_expressiveness",
                ))
                    
        return components, evidence

    def _keyword_based_compute(self, ctx: SessionContext) -> MetricResult:
        """V2 keyword-based fallback logic."""
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        phys_components, phys_evidence = self._get_physiological_signals(ctx)
        components.extend(phys_components)
        evidence.extend(phys_evidence)

        # ── Signal: Response depth ─────────────────────────────────────
        if ctx.transcripts:
            n = len(ctx.transcripts)
            sig_confidence = sample_size_confidence(
                n, self.MIN_TRANSCRIPT_CHUNKS, self.IDEAL_TRANSCRIPT_CHUNKS
            )
            if sig_confidence > 0:
                avg_length = sum(
                    len(t.get("text", "").split()) for t in ctx.transcripts
                ) / max(n, 1)

                depth_score = int(min(avg_length / 30 * 100, 100))

                components.append(SignalComponent(
                    score=max(0, min(100, depth_score)),
                    confidence=sig_confidence,
                    signal_name="response_depth",
                ))

                if avg_length < 15:
                    evidence.append({
                        "quote": f"Average response length was {avg_length:.0f} words per chunk (brief responses)",
                        "timestamp": "",
                        "source": "transcript_analysis",
                    })

        # ── Signal: Question interaction ───────────────────────────────
        if ctx.questions:
            n = len(ctx.questions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_QUESTIONS, self.IDEAL_QUESTIONS
            )
            if sig_confidence > 0:
                asked = [q for q in ctx.questions if q.get("was_asked")]
                if asked:
                    ask_ratio = len(asked) / n
                    question_score = int(ask_ratio * 100)

                    components.append(SignalComponent(
                        score=max(0, min(100, question_score)),
                        confidence=sig_confidence,
                        signal_name="question_interaction",
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
                explanation="Insufficient data to assess engagement.",
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
                f"Engagement assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(EngagementMetric())
