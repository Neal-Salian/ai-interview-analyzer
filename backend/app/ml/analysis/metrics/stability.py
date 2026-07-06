"""
Emotional stability metric plugin — Enterprise Competency Framework.

Assesses how emotionally consistent the candidate remains throughout
the interview.

V3.0: Evidence-first evaluation. Integrates structured evidence (from the
preprocessing pipeline) with physiological signals (emotions).
Falls back to pure physiological analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with raised sample-size thresholds,
      EMA smoothing, outlier filtering, and per-signal confidence breakdown.
"""

from collections import Counter

from app.ml.analysis.interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
)
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    ema_smooth,
    score_to_level,
    evidence_based_confidence,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class StabilityMetric:
    name = "Emotional Stability"
    description = (
        "Measures how emotionally consistent the candidate remains "
        "throughout the interview, including mood shifts and recovery "
        "from negative emotion spikes."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

    NEGATIVE_EMOTIONS = {"angry", "fear", "sad", "disgust"}
    POSITIVE_EMOTIONS = {"happy", "surprise"}

    # Minimum data thresholds
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            rel_types = ["emotional_consistency", "composure", "recovery"]
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
        """Score stability using pre-extracted behaviour evidence combined with raw physiological signals."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        avg_confidence = sum(b.confidence for b in behaviours) / len(behaviours)
        base_score = min(int(len(behaviours) * 20 + avg_confidence * 20), 100)

        components.append(SignalComponent(
            score=max(0, min(100, base_score)),
            confidence=avg_confidence,
            signal_name="emotional_consistency_behaviours",
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
                f"Combined behavioural composure analysis with physiological emotion signals "
                f"({len(phys_components)} sensor metrics used)."
            )
        else:
            reasoning_parts.append(
                "Assessed based on transcript-level consistency (physiological data unavailable)."
            )
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Demonstrated emotional consistency. Likely to remain steady in unpredictable situations."
            )
        else:
            recommendations.append(
                "Observed some emotional fluctuation. Ensure role expectations are clearly defined to minimize unexpected stressors."
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
                f"Emotional stability assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"emotional stability and consistency."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _get_physiological_signals(self, ctx: SessionContext) -> tuple[list[SignalComponent], list[dict]]:
        """Extract physiological stability signals (used in both V2 and V3)."""
        components = []
        evidence = []

        if not ctx.emotions or len(ctx.emotions) < self.MIN_EMOTION_FRAMES:
            return components, evidence

        total = len(ctx.emotions)
        base_confidence = sample_size_confidence(
            total, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
        )

        # ── Signal 1: Mood shift frequency ───────────────────────────────
        emotion_map = {"neutral": 0, "happy": 1, "surprise": 1,
                       "sad": -1, "angry": -2, "fear": -2, "disgust": -1}
        numeric_emotions = [
            emotion_map.get(e.get("dominant_emotion", "neutral"), 0)
            for e in ctx.emotions
        ]
        smoothed = ema_smooth(numeric_emotions, alpha=0.3)

        shifts = 0
        for i in range(1, len(smoothed)):
            prev_category = round(smoothed[i - 1])
            curr_category = round(smoothed[i])
            if prev_category != curr_category:
                shifts += 1

        shift_ratio = shifts / (total - 1) if total > 1 else 0
        shift_score = int((1 - shift_ratio) * 100)

        components.append(SignalComponent(
            score=max(0, min(100, shift_score)),
            confidence=base_confidence,
            signal_name="mood_shift_frequency",
        ))

        if shift_ratio > 0.5:
            evidence.append({
                "quote": f"Emotion changed {shifts} times across {total} frames ({shift_ratio:.0%} shift rate)",
                "timestamp": "",
                "source": "emotion_detection",
            })

        # ── Signal 2: Negative emotion ratio ─────────────────────────────
        neg_count = sum(
            1 for e in ctx.emotions
            if e.get("dominant_emotion") in self.NEGATIVE_EMOTIONS
        )
        neg_ratio = neg_count / total
        neg_score = int((1 - neg_ratio) * 100)

        components.append(SignalComponent(
            score=max(0, min(100, neg_score)),
            confidence=base_confidence,
            signal_name="negative_emotion_ratio",
        ))

        # ── Signal 3: Recovery time ──────────────────────────────────────
        recovery_times: list[int] = []
        in_negative = False
        negative_streak = 0

        for e in ctx.emotions:
            emotion = e.get("dominant_emotion", "")
            if emotion in self.NEGATIVE_EMOTIONS:
                in_negative = True
                negative_streak += 1
            elif in_negative:
                recovery_times.append(negative_streak)
                in_negative = False
                negative_streak = 0

        if recovery_times:
            avg_recovery = sum(recovery_times) / len(recovery_times)
            recovery_score = int(max(0, 100 - (avg_recovery - 1) * 25))
            recovery_confidence = min(base_confidence, sample_size_confidence(
                len(recovery_times), 2, 8
            ))

            components.append(SignalComponent(
                score=max(0, min(100, recovery_score)),
                confidence=max(0.1, recovery_confidence),
                signal_name="recovery_time",
            ))

            if avg_recovery > 3:
                evidence.append({
                    "quote": f"Average recovery from negative emotions took {avg_recovery:.1f} frames",
                    "timestamp": "",
                    "source": "emotion_detection",
                })
        else:
            if neg_count == 0:
                components.append(SignalComponent(
                    score=85,
                    confidence=base_confidence * 0.3,
                    signal_name="recovery_time",
                ))

        # ── Signal 4: Baseline consistency ───────────────────────────────
        emotion_counts = Counter(
            e.get("dominant_emotion") for e in ctx.emotions
        )
        if emotion_counts:
            most_common_emotion, most_common_count = emotion_counts.most_common(1)[0]
            dominance_ratio = most_common_count / total

            is_positive_baseline = most_common_emotion in (
                self.POSITIVE_EMOTIONS | {"neutral"}
            )
            if is_positive_baseline:
                baseline_score = int(dominance_ratio * 100)
            else:
                baseline_score = int((1 - dominance_ratio) * 100)

            components.append(SignalComponent(
                score=max(0, min(100, baseline_score)),
                confidence=base_confidence,
                signal_name="baseline_consistency",
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
                explanation="Insufficient data to assess stability.",
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
                f"Emotional stability assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(StabilityMetric())
