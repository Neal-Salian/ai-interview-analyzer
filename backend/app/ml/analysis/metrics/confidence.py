"""
Confidence metric plugin.

Assesses candidate confidence based on:
  - Emotion stability (fewer negative spikes)
  - Filler word frequency in transcript
  - Gaze steadiness (when attention data is available)
  - Voice steadiness indicators from emotion confidence variance

v2.0: Confidence-weighted scoring with sample-size guards, outlier
      filtering, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import MetricResult, SessionContext
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    keyword_density_confidence,
    remove_outliers_iqr,
    ema_smooth,
    score_to_level,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class ConfidenceMetric:
    name = "Confidence"
    description = (
        "Assesses candidate confidence based on vocal steadiness, "
        "emotion stability, and gaze patterns."
    )
    version = "2.0"

    # Filler words commonly misheard or actually spoken
    FILLERS = [
        "um", "uh", "like", "you know", "basically", "actually",
        "sort of", "kind of", "i mean", "right", "so yeah",
    ]

    # Minimum data thresholds
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50
    MIN_TRANSCRIPT_WORDS = 50
    IDEAL_TRANSCRIPT_WORDS = 200
    MIN_ATTENTION_EVENTS = 5
    IDEAL_ATTENTION_EVENTS = 30
    MIN_VARIANCE_FRAMES = 10
    IDEAL_VARIANCE_FRAMES = 40

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        # ── Signal 1: Emotion stability ──────────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                negative_emotions = {"angry", "fear", "sad", "disgust"}
                negative_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in negative_emotions
                )
                negative_ratio = negative_count / n
                emotion_score = int((1.0 - negative_ratio) * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, emotion_score)),
                    confidence=sig_confidence,
                    signal_name="emotion_stability",
                ))

                if negative_ratio > 0.3:
                    evidence.append({
                        "quote": f"{negative_count}/{n} frames showed negative emotions",
                        "timestamp": ctx.emotions[-1].get("timestamp", ""),
                        "source": "emotion_detection",
                    })

        # ── Signal 2: Filler word frequency ──────────────────────────────
        if ctx.candidate_transcript:
            text_lower = ctx.candidate_transcript.lower()
            words = text_lower.split()
            word_count = max(len(words), 1)

            sig_confidence = keyword_density_confidence(
                hits=0,  # we'll compute below
                word_count=word_count,
                min_words=self.MIN_TRANSCRIPT_WORDS,
                ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
            )
            if sig_confidence > 0:
                filler_count = sum(
                    text_lower.count(filler) for filler in self.FILLERS
                )
                filler_ratio = filler_count / word_count

                # Recompute with actual hits for proper confidence
                sig_confidence = keyword_density_confidence(
                    hits=max(filler_count, 1),  # at least 1 to get length-based confidence
                    word_count=word_count,
                    min_words=self.MIN_TRANSCRIPT_WORDS,
                    ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
                )

                # Low filler ratio = high confidence
                # 0% fillers → 100, 5%+ fillers → ~0
                filler_score = int(max(0, (1.0 - filler_ratio * 20)) * 100)
                filler_score = max(0, min(100, filler_score))

                components.append(SignalComponent(
                    score=filler_score,
                    confidence=sig_confidence,
                    signal_name="filler_word_ratio",
                ))

                if filler_ratio > 0.03:
                    evidence.append({
                        "quote": f"Filler words detected: ~{filler_count} instances in {word_count} words ({filler_ratio:.1%})",
                        "timestamp": "",
                        "source": "transcript_analysis",
                    })

        # ── Signal 3: Gaze steadiness ────────────────────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                center_count = sum(
                    1 for a in ctx.attention_events
                    if a.get("direction") == "center"
                )
                center_ratio = center_count / n
                gaze_score = int(center_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, gaze_score)),
                    confidence=sig_confidence,
                    signal_name="gaze_steadiness",
                ))

                if center_ratio < 0.5:
                    evidence.append({
                        "quote": f"Eye contact maintained {center_ratio:.0%} of the time",
                        "timestamp": "",
                        "source": "attention_tracking",
                    })

        # ── Signal 4: Emotion confidence variance ────────────────────────
        if ctx.emotions and len(ctx.emotions) >= self.MIN_VARIANCE_FRAMES:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_VARIANCE_FRAMES, self.IDEAL_VARIANCE_FRAMES
            )

            raw_confidences = [e.get("confidence", 0) for e in ctx.emotions]
            # Remove outliers before computing variance
            cleaned = remove_outliers_iqr(raw_confidences)
            # Smooth to reduce frame-to-frame noise
            smoothed = ema_smooth(cleaned, alpha=0.3)

            if smoothed:
                avg = sum(smoothed) / len(smoothed)
                variance = sum((c - avg) ** 2 for c in smoothed) / len(smoothed)
                # Lower variance = more consistent = more confident
                # Normalize: variance < 100 is very stable, > 500 is very unstable
                stability_score = int(max(0, min(100, 100 - (variance / 5))))

                components.append(SignalComponent(
                    score=stability_score,
                    confidence=sig_confidence,
                    signal_name="emotion_confidence_consistency",
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
                explanation="Insufficient data to assess confidence.",
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
                f"Confidence assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(ConfidenceMetric())
