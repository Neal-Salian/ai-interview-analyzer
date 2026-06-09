"""
Stress indicators metric plugin.

Detects observable stress signals — NOT a psychological diagnosis.

Signals:
  - Negative emotion spikes (fear, angry clusters)
  - Speaking pace variance (rapid/slow shifts in transcript chunk lengths)
  - Gaze instability (frequent direction changes)
  - Integrity events (face missing, multiple faces under pressure)
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class StressMetric:
    name = "Stress Indicators"
    description = (
        "Detects observable stress signals based on emotion patterns, "
        "speech variance, and behavioral consistency. "
        "Reports observable signals only — not a clinical assessment."
    )
    version = "1.0"

    STRESS_EMOTIONS = {"angry", "fear", "disgust"}

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        # For stress, higher internal score = MORE stress detected
        # We invert at the end: final_score = 100 - stress_level
        # So a "low stress" session gets a HIGH score (good)
        stress_components: list[int] = []

        # ── Signal 1: Negative emotion clusters ─────────────────────────
        if ctx.emotions and len(ctx.emotions) >= 3:
            total = len(ctx.emotions)
            stress_count = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") in self.STRESS_EMOTIONS
            )
            stress_ratio = stress_count / total

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

            stress_components.append(emotion_stress)
            signals.append("emotion_stress_patterns")

        # ── Signal 2: Speaking pace variance ─────────────────────────────
        if ctx.transcripts and len(ctx.transcripts) >= 3:
            chunk_lengths = [
                len(t.get("text", "").split()) for t in ctx.transcripts
            ]
            avg_len = sum(chunk_lengths) / len(chunk_lengths)
            if avg_len > 0:
                variance = sum(
                    (l - avg_len) ** 2 for l in chunk_lengths
                ) / len(chunk_lengths)
                # High variance = inconsistent speaking pace = stress signal
                # Normalize: variance < 50 is stable, > 200 is very erratic
                pace_stress = int(min(variance / 2, 100))
                stress_components.append(pace_stress)
                signals.append("speaking_pace_variance")

                if pace_stress > 50:
                    evidence.append({
                        "quote": f"Speaking pace showed high variance (some responses much shorter/longer than average)",
                        "timestamp": "",
                        "source": "transcript_analysis",
                    })

        # ── Signal 3: Gaze instability ───────────────────────────────────
        if ctx.attention_events and len(ctx.attention_events) >= 5:
            direction_changes = 0
            prev_dir = None
            for a in ctx.attention_events:
                curr_dir = a.get("direction")
                if prev_dir and curr_dir != prev_dir:
                    direction_changes += 1
                prev_dir = curr_dir

            change_ratio = direction_changes / len(ctx.attention_events)
            # High change ratio = restless gaze = stress signal
            gaze_stress = int(min(change_ratio * 150, 100))
            stress_components.append(gaze_stress)
            signals.append("gaze_instability")

        # ── Signal 4: Integrity-related stress ───────────────────────────
        if ctx.integrity_events:
            warning_count = sum(
                1 for ie in ctx.integrity_events
                if ie.get("severity") in ("warning", "critical")
            )
            if warning_count > 0:
                # Some integrity warnings may correlate with stress
                integrity_stress = int(min(warning_count * 15, 60))
                stress_components.append(integrity_stress)
                signals.append("behavioral_anomalies")

        # ── Aggregate ────────────────────────────────────────────────────
        if not stress_components:
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="Insufficient data to assess stress indicators.",
                signals_used=[],
            )

        avg_stress = int(sum(stress_components) / len(stress_components))
        # Invert: high stress_level → low score (stress is undesirable)
        # But we frame it as "Composure" — higher = more composed
        final_score = max(0, min(100, 100 - avg_stress))
        assessment_confidence = min(len(stress_components) / 4, 1.0)

        return MetricResult(
            name=self.name,
            score=final_score,
            level=score_to_level(final_score),
            confidence=round(assessment_confidence, 2),
            evidence=evidence,
            explanation=(
                f"Stress indicators assessed using {len(stress_components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Higher score indicates greater composure under pressure."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(StressMetric())
