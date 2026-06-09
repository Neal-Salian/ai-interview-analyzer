"""
Emotional stability metric plugin.

Assesses how emotionally consistent the candidate remains throughout
the interview.

Signals:
  - Emotion variance over time
  - Mood shift frequency (how often dominant emotion changes)
  - Recovery time after negative emotion spikes
  - Sustained positive/neutral baseline
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class StabilityMetric:
    name = "Emotional Stability"
    description = (
        "Measures how emotionally consistent the candidate remains "
        "throughout the interview, including mood shifts and recovery "
        "from negative emotion spikes."
    )
    version = "1.0"

    NEGATIVE_EMOTIONS = {"angry", "fear", "sad", "disgust"}
    POSITIVE_EMOTIONS = {"happy", "surprise"}

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        score_components: list[int] = []

        if not ctx.emotions or len(ctx.emotions) < 3:
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="Insufficient emotion data (need at least 3 frames).",
                signals_used=[],
            )

        total = len(ctx.emotions)

        # ── Signal 1: Mood shift frequency ───────────────────────────────
        shifts = 0
        for i in range(1, total):
            prev = ctx.emotions[i - 1].get("dominant_emotion")
            curr = ctx.emotions[i].get("dominant_emotion")
            if prev != curr:
                shifts += 1

        shift_ratio = shifts / (total - 1)
        # Lower shift ratio = more stable
        # 0% shifts → 100, 80%+ shifts → ~0
        shift_score = int((1 - shift_ratio) * 100)
        score_components.append(max(0, min(100, shift_score)))
        signals.append("mood_shift_frequency")

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
        score_components.append(max(0, min(100, neg_score)))
        signals.append("negative_emotion_ratio")

        # ── Signal 3: Recovery time ──────────────────────────────────────
        # How quickly does the candidate return to neutral/positive
        # after a negative spike?
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
            score_components.append(max(0, min(100, recovery_score)))
            signals.append("recovery_time")

            if avg_recovery > 3:
                evidence.append({
                    "quote": f"Average recovery from negative emotions took {avg_recovery:.1f} frames",
                    "timestamp": "",
                    "source": "emotion_detection",
                })

        # ── Signal 4: Baseline consistency ───────────────────────────────
        # Is there a stable baseline emotion throughout?
        from collections import Counter
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

        score_components.append(max(0, min(100, baseline_score)))
        signals.append("baseline_consistency")

        # ── Aggregate ────────────────────────────────────────────────────
        final_score = int(sum(score_components) / len(score_components))
        assessment_confidence = min(len(score_components) / 4, 1.0)

        return MetricResult(
            name=self.name,
            score=final_score,
            level=score_to_level(final_score),
            confidence=round(assessment_confidence, 2),
            evidence=evidence,
            explanation=(
                f"Emotional stability assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(StabilityMetric())
