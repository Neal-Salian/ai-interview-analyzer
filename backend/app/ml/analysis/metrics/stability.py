"""
Emotional stability metric plugin.

Assesses how emotionally consistent the candidate remains throughout
the interview.

Signals:
  - Emotion variance over time
  - Mood shift frequency (how often dominant emotion changes)
  - Recovery time after negative emotion spikes
  - Sustained positive/neutral baseline

v2.0: Confidence-weighted scoring with raised sample-size thresholds,
      EMA smoothing, outlier filtering, and per-signal confidence breakdown.
"""

from collections import Counter

from app.ml.analysis.interfaces import MetricResult, SessionContext
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    ema_smooth,
    score_to_level,
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
    version = "2.0"

    NEGATIVE_EMOTIONS = {"angry", "fear", "sad", "disgust"}
    POSITIVE_EMOTIONS = {"happy", "surprise"}

    # Minimum data thresholds — raised from v1.0
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        if not ctx.emotions or len(ctx.emotions) < self.MIN_EMOTION_FRAMES:
            return MetricResult(
                name=self.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                confidence_details=[],
                evidence=[],
                explanation=(
                    f"Insufficient emotion data (need at least "
                    f"{self.MIN_EMOTION_FRAMES} frames, got {len(ctx.emotions) if ctx.emotions else 0})."
                ),
                signals_used=[],
            )

        total = len(ctx.emotions)
        base_confidence = sample_size_confidence(
            total, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
        )

        # ── Signal 1: Mood shift frequency ───────────────────────────────
        # Apply EMA smoothing to emotion sequence to reduce noise
        # Map emotions to numeric values for smoothing
        emotion_map = {"neutral": 0, "happy": 1, "surprise": 1,
                       "sad": -1, "angry": -2, "fear": -2, "disgust": -1}
        numeric_emotions = [
            emotion_map.get(e.get("dominant_emotion", "neutral"), 0)
            for e in ctx.emotions
        ]
        smoothed = ema_smooth(numeric_emotions, alpha=0.3)

        # Count shifts on smoothed sequence (threshold crossings)
        shifts = 0
        for i in range(1, len(smoothed)):
            # A shift occurs when the smoothed value crosses an integer boundary
            prev_category = round(smoothed[i - 1])
            curr_category = round(smoothed[i])
            if prev_category != curr_category:
                shifts += 1

        shift_ratio = shifts / (total - 1) if total > 1 else 0
        # Lower shift ratio = more stable
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
            # 1-2 frames recovery = excellent, 5+ = slow recovery
            recovery_score = int(max(0, 100 - (avg_recovery - 1) * 25))
            # Recovery confidence scales with number of recovery events observed
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
            # No recovery events observed — either no negative emotions (good)
            # or never recovered (bad, but unlikely without recovery data).
            # Contribute a low-confidence neutral signal.
            if neg_count == 0:
                components.append(SignalComponent(
                    score=85,  # no negative emotions is positive
                    confidence=base_confidence * 0.3,
                    signal_name="recovery_time",
                ))

        # ── Signal 4: Baseline consistency ───────────────────────────────
        emotion_counts = Counter(
            e.get("dominant_emotion") for e in ctx.emotions
        )
        most_common_emotion, most_common_count = emotion_counts.most_common(1)[0]
        dominance_ratio = most_common_count / total

        # High dominance of neutral/positive = stable baseline
        is_positive_baseline = most_common_emotion in (
            self.POSITIVE_EMOTIONS | {"neutral"}
        )
        if is_positive_baseline:
            baseline_score = int(dominance_ratio * 100)
        else:
            # Dominant negative emotion = unstable baseline
            baseline_score = int((1 - dominance_ratio) * 100)

        components.append(SignalComponent(
            score=max(0, min(100, baseline_score)),
            confidence=base_confidence,
            signal_name="baseline_consistency",
        ))

        # ── Aggregate ────────────────────────────────────────────────────
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
