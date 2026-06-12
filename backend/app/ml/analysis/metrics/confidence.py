"""
Confidence metric plugin.

Assesses candidate confidence based on:
  - Emotion stability (fewer negative spikes)
  - Filler word frequency in transcript
  - Gaze steadiness (when attention data is available)
  - Voice steadiness indicators from emotion confidence variance
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class ConfidenceMetric:
    name = "Confidence"
    description = (
        "Assesses candidate confidence based on vocal steadiness, "
        "emotion stability, and gaze patterns."
    )
    version = "1.0"

    # Filler words commonly misheard or actually spoken
    FILLERS = [
        "um", "uh", "like", "you know", "basically", "actually",
        "sort of", "kind of", "i mean", "right", "so yeah",
    ]

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        score_components: list[int] = []

        # ── Signal 1: Emotion stability ──────────────────────────────────
        if ctx.emotions:
            negative_emotions = {"angry", "fear", "sad", "disgust"}
            total = len(ctx.emotions)
            negative_count = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") in negative_emotions
            )
            negative_ratio = negative_count / total
            emotion_score = int((1.0 - negative_ratio) * 100)
            score_components.append(emotion_score)
            signals.append("emotion_stability")

            if negative_ratio > 0.3:
                evidence.append({
                    "quote": f"{negative_count}/{total} frames showed negative emotions",
                    "timestamp": ctx.emotions[-1].get("timestamp", ""),
                    "source": "emotion_detection",
                })

        # ── Signal 2: Filler word frequency ──────────────────────────────
        if ctx.full_transcript:
            text_lower = ctx.full_transcript.lower()
            words = text_lower.split()
            word_count = max(len(words), 1)

            filler_count = sum(
                text_lower.count(filler) for filler in self.FILLERS
            )
            filler_ratio = filler_count / word_count

            # Low filler ratio = high confidence
            # 0% fillers → 100, 5%+ fillers → ~0
            filler_score = int(max(0, (1.0 - filler_ratio * 20)) * 100)
            filler_score = max(0, min(100, filler_score))
            score_components.append(filler_score)
            signals.append("filler_word_ratio")

            if filler_ratio > 0.03:
                evidence.append({
                    "quote": f"Filler words detected: ~{filler_count} instances in {word_count} words ({filler_ratio:.1%})",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 3: Gaze steadiness ────────────────────────────────────
        if ctx.attention_events:
            total_attn = len(ctx.attention_events)
            center_count = sum(
                1 for a in ctx.attention_events
                if a.get("direction") == "center"
            )
            center_ratio = center_count / total_attn
            gaze_score = int(center_ratio * 100)
            score_components.append(gaze_score)
            signals.append("gaze_steadiness")

            if center_ratio < 0.5:
                evidence.append({
                    "quote": f"Eye contact maintained {center_ratio:.0%} of the time",
                    "timestamp": "",
                    "source": "attention_tracking",
                })

        # ── Signal 4: Emotion confidence variance ────────────────────────
        if ctx.emotions and len(ctx.emotions) >= 5:
            confidences = [e.get("confidence", 0) for e in ctx.emotions]
            avg = sum(confidences) / len(confidences)
            variance = sum((c - avg) ** 2 for c in confidences) / len(confidences)
            # Lower variance = more consistent = more confident
            # Normalize: variance < 100 is very stable, > 500 is very unstable
            stability_score = int(max(0, min(100, 100 - (variance / 5))))
            score_components.append(stability_score)
            signals.append("emotion_confidence_consistency")

        # ── Aggregate ────────────────────────────────────────────────────
        if not score_components:
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="Insufficient data to assess confidence.",
                signals_used=[],
            )

        final_score = int(sum(score_components) / len(score_components))
        # Confidence in the assessment itself scales with signal count
        assessment_confidence = min(len(score_components) / 4, 1.0)

        return MetricResult(
            name=self.name,
            score=final_score,
            level=score_to_level(final_score),
            confidence=round(assessment_confidence, 2),
            evidence=evidence,
            explanation=(
                f"Confidence assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(ConfidenceMetric())
