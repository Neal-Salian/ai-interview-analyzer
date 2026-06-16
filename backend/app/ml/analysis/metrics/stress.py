"""
Stress indicators metric plugin.

Detects observable stress signals — NOT a psychological diagnosis.

Signals:
  - Negative emotion spikes (fear, angry clusters)
  - Speaking pace variance (rapid/slow shifts in transcript chunk lengths)
  - Gaze instability (frequent direction changes)
  - Integrity events (face missing, multiple faces under pressure)

v2.0: Confidence-weighted scoring with raised sample-size thresholds,
      outlier removal on pace variance, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import MetricResult, SessionContext
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    remove_outliers_iqr,
    score_to_level,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class StressMetric:
    name = "Stress Indicators"
    description = (
        "Detects observable stress signals based on emotion patterns, "
        "speech variance, and behavioral consistency. "
        "Reports observable signals only — not a clinical assessment."
    )
    version = "2.0"

    STRESS_EMOTIONS = {"angry", "fear", "disgust"}

    # Minimum data thresholds — raised from v1.0
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50
    MIN_TRANSCRIPT_CHUNKS = 5
    IDEAL_TRANSCRIPT_CHUNKS = 15
    MIN_ATTENTION_EVENTS = 10
    IDEAL_ATTENTION_EVENTS = 40
    MIN_INTEGRITY_EVENTS = 3
    IDEAL_INTEGRITY_EVENTS = 10

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []
        # For stress, higher internal score = MORE stress detected
        # We invert at the end: final_score = 100 - stress_level

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

                # Check for clusters (3+ consecutive stress emotions)
                cluster_count = 0
                streak = 0
                for e in ctx.emotions:
                    if e.get("dominant_emotion") in self.STRESS_EMOTIONS:
                        streak += 1
                        if streak >= 3:
                            cluster_count += 1
                    else:
                        streak = 0

                # stress_ratio contributes 0-100 (higher = more stress)
                emotion_stress = int(stress_ratio * 100)
                if cluster_count > 0:
                    emotion_stress = min(100, emotion_stress + cluster_count * 10)
                    evidence.append({
                        "quote": f"{cluster_count} cluster(s) of 3+ consecutive stress-related emotions detected",
                        "timestamp": "",
                        "source": "emotion_detection",
                    })

                # Invert: high stress → low composure score
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
                # Apply outlier removal to reduce noise from transcription artifacts
                cleaned_lengths = remove_outliers_iqr(
                    [float(l) for l in chunk_lengths]
                )
                avg_len = sum(cleaned_lengths) / max(len(cleaned_lengths), 1)
                if avg_len > 0 and len(cleaned_lengths) >= 3:
                    variance = sum(
                        (l - avg_len) ** 2 for l in cleaned_lengths
                    ) / len(cleaned_lengths)
                    # High variance = inconsistent pace = stress signal
                    # Normalize: variance < 50 is stable, > 200 is very erratic
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
                # High change ratio = restless gaze = stress signal
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
                # Cap confidence at 0.5 for < MIN_INTEGRITY_EVENTS events
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
