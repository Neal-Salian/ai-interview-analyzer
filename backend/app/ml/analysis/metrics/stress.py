"""
Stress indicators metric plugin — Enterprise Competency Framework.

Detects observable stress signals — NOT a psychological diagnosis.

V3.0: Evidence-first evaluation. Integrates structured evidence (from the
preprocessing pipeline) with physiological signals (emotions, attention).
Falls back to pure physiological analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with raised sample-size thresholds,
      outlier removal on pace variance, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
)
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    remove_outliers_iqr,
    score_to_level,
    evidence_based_confidence,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class StressMetric:
    name = "Stress Indicators"
    description = (
        "Detects observable stress signals based on emotion patterns, "
        "speech variance, behavioral consistency, and pressure management. "
        "Reports observable signals only — not a clinical assessment."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    STRESS_EMOTIONS = {"angry", "fear", "disgust"}

    # Minimum data thresholds
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50
    MIN_TRANSCRIPT_CHUNKS = 5
    IDEAL_TRANSCRIPT_CHUNKS = 15
    MIN_ATTENTION_EVENTS = 10
    IDEAL_ATTENTION_EVENTS = 40
    MIN_INTEGRITY_EVENTS = 3
    IDEAL_INTEGRITY_EVENTS = 10

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            rel_types = ["pressure_management", "stress_handling", "composure"]
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
        """Score stress using pre-extracted behaviour evidence combined with raw physiological signals."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        avg_confidence = sum(b.confidence for b in behaviours) / len(behaviours)
        base_score = min(int(len(behaviours) * 20 + avg_confidence * 20), 100)

        components.append(SignalComponent(
            score=max(0, min(100, base_score)),
            confidence=avg_confidence,
            signal_name="composure_behaviours",
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
                f"Combined behavioural composure analysis with physiological stress signals "
                f"({len(phys_components)} sensor metrics used)."
            )
        else:
            reasoning_parts.append(
                "Assessed based on transcript-level composure (physiological data unavailable)."
            )
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Strong composure under pressure. Suitable for high-stakes or time-sensitive roles."
            )
        else:
            recommendations.append(
                "Observable stress indicators present. Provide a supportive onboarding environment."
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
                f"Stress indicators assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"composure and pressure management."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _get_physiological_signals(self, ctx: SessionContext) -> tuple[list[SignalComponent], list[dict]]:
        """Extract physiological stress signals (used in both V2 and V3)."""
        components = []
        evidence = []

        # ── Signal 1: Negative emotion clusters ─────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                stress_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in self.STRESS_EMOTIONS
                )
                stress_ratio = stress_count / n

                cluster_count = 0
                streak = 0
                for e in ctx.emotions:
                    if e.get("dominant_emotion") in self.STRESS_EMOTIONS:
                        streak += 1
                        if streak >= 3:
                            cluster_count += 1
                    else:
                        streak = 0

                emotion_stress = int(stress_ratio * 100)
                if cluster_count > 0:
                    emotion_stress = min(100, emotion_stress + cluster_count * 10)
                    evidence.append({
                        "quote": f"{cluster_count} cluster(s) of 3+ consecutive stress-related emotions detected",
                        "timestamp": "",
                        "source": "emotion_detection",
                    })

                composure_score = max(0, min(100, 100 - emotion_stress))
                components.append(SignalComponent(
                    score=composure_score,
                    confidence=sig_confidence,
                    signal_name="emotion_stress_patterns",
                ))

        # ── Signal 2: Speaking pace variance ─────────────────────────────
        if ctx.transcripts:
            n = len(ctx.transcripts)
            sig_confidence = sample_size_confidence(
                n, self.MIN_TRANSCRIPT_CHUNKS, self.IDEAL_TRANSCRIPT_CHUNKS
            )
            if sig_confidence > 0:
                chunk_lengths = [
                    len(t.get("text", "").split()) for t in ctx.transcripts
                ]
                cleaned_lengths = remove_outliers_iqr([float(l) for l in chunk_lengths])
                avg_len = sum(cleaned_lengths) / max(len(cleaned_lengths), 1)
                if avg_len > 0 and len(cleaned_lengths) >= 3:
                    variance = sum(
                        (l - avg_len) ** 2 for l in cleaned_lengths
                    ) / len(cleaned_lengths)
                    pace_stress = int(min(variance / 2, 100))
                    composure_score = max(0, min(100, 100 - pace_stress))

                    components.append(SignalComponent(
                        score=composure_score,
                        confidence=sig_confidence,
                        signal_name="speaking_pace_variance",
                    ))

                    if pace_stress > 50:
                        evidence.append({
                            "quote": "Speaking pace showed high variance (some responses much shorter/longer than average)",
                            "timestamp": "",
                            "source": "transcript_analysis",
                        })

        # ── Signal 3: Gaze instability ───────────────────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                direction_changes = 0
                prev_dir = None
                for a in ctx.attention_events:
                    curr_dir = a.get("direction")
                    if prev_dir and curr_dir != prev_dir:
                        direction_changes += 1
                    prev_dir = curr_dir

                change_ratio = direction_changes / n
                gaze_stress = int(min(change_ratio * 150, 100))
                composure_score = max(0, min(100, 100 - gaze_stress))

                components.append(SignalComponent(
                    score=composure_score,
                    confidence=sig_confidence,
                    signal_name="gaze_instability",
                ))

        # ── Signal 4: Integrity-related stress ───────────────────────────
        if ctx.integrity_events:
            n = len(ctx.integrity_events)
            warning_count = sum(
                1 for ie in ctx.integrity_events
                if ie.get("severity") in ("warning", "critical")
            )
            if warning_count > 0:
                sig_confidence = min(
                    sample_size_confidence(
                        n, self.MIN_INTEGRITY_EVENTS, self.IDEAL_INTEGRITY_EVENTS
                    ),
                    0.5,
                )
                if sig_confidence > 0:
                    integrity_stress = int(min(warning_count * 15, 60))
                    composure_score = max(0, min(100, 100 - integrity_stress))

                    components.append(SignalComponent(
                        score=composure_score,
                        confidence=sig_confidence,
                        signal_name="behavioral_anomalies",
                    ))

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
                explanation="Insufficient data to assess stress indicators.",
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
                f"Stress indicators assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Higher score indicates greater composure under pressure. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(StressMetric())
