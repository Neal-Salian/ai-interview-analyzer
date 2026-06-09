"""
Attention metric plugin.

Assesses how attentive and focused the candidate was during the interview.

Signals:
  - Eye contact ratio (center gaze %)
  - Face-missing frequency (distraction indicator)
  - Gaze direction distribution (balanced vs. erratic)
  - Attention consistency over time (stable vs. degrading)
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class AttentionMetric:
    name = "Attention"
    description = (
        "Measures candidate focus and attentiveness based on gaze patterns, "
        "face visibility, and attention consistency throughout the interview."
    )
    version = "1.0"

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        score_components: list[int] = []

        # ── Signal 1: Eye contact ratio ──────────────────────────────────
        if ctx.attention_events:
            total = len(ctx.attention_events)
            center = sum(
                1 for a in ctx.attention_events
                if a.get("direction") == "center"
            )
            center_ratio = center / total
            eye_score = int(center_ratio * 100)
            score_components.append(max(0, min(100, eye_score)))
            signals.append("eye_contact_ratio")

            evidence.append({
                "quote": f"Direct eye contact maintained {center_ratio:.0%} of the time ({center}/{total} frames)",
                "timestamp": "",
                "source": "attention_tracking",
            })

        # ── Signal 2: Face-missing frequency ─────────────────────────────
        if ctx.attention_events:
            total = len(ctx.attention_events)
            missing = sum(
                1 for a in ctx.attention_events
                if a.get("direction") == "missing"
            )
            missing_ratio = missing / total
            # 0% missing → 100 score, 30%+ missing → 0
            presence_score = int(max(0, (1 - missing_ratio * 3.3)) * 100)
            score_components.append(max(0, min(100, presence_score)))
            signals.append("face_visibility")

            if missing_ratio > 0.1:
                evidence.append({
                    "quote": f"Face was not visible in {missing_ratio:.0%} of frames",
                    "timestamp": "",
                    "source": "attention_tracking",
                })

        # ── Signal 3: Attention consistency over time ────────────────────
        if ctx.attention_events and len(ctx.attention_events) >= 10:
            # Compare first half vs second half attention
            mid = len(ctx.attention_events) // 2
            first_half = ctx.attention_events[:mid]
            second_half = ctx.attention_events[mid:]

            first_center = sum(
                1 for a in first_half if a.get("direction") == "center"
            ) / max(len(first_half), 1)
            second_center = sum(
                1 for a in second_half if a.get("direction") == "center"
            ) / max(len(second_half), 1)

            # If attention drops significantly in the second half, lower score
            drop = first_center - second_center
            if drop > 0.2:
                consistency_score = int((1 - drop) * 100)
                evidence.append({
                    "quote": f"Eye contact dropped from {first_center:.0%} to {second_center:.0%} in the second half",
                    "timestamp": "",
                    "source": "attention_tracking",
                })
            else:
                consistency_score = 80  # maintained or improved
            score_components.append(max(0, min(100, consistency_score)))
            signals.append("attention_consistency")

        # ── Fallback: Use emotion data if no attention data ──────────────
        if not ctx.attention_events and ctx.emotions:
            # Without attention tracking, use emotion engagement as proxy
            neutral_ratio = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") == "neutral"
            ) / max(len(ctx.emotions), 1)
            # Extremely high neutral ratio may indicate disengagement
            proxy_score = int((1 - max(0, neutral_ratio - 0.5) * 2) * 100)
            score_components.append(max(0, min(100, proxy_score)))
            signals.append("emotion_engagement_proxy")
            evidence.append({
                "quote": "Attention estimated from emotion data (no gaze tracking available)",
                "timestamp": "",
                "source": "emotion_detection",
            })

        # ── Aggregate ────────────────────────────────────────────────────
        if not score_components:
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="Insufficient data to assess attention.",
                signals_used=[],
            )

        final_score = int(sum(score_components) / len(score_components))
        # Attention confidence is higher when we have actual gaze data
        has_gaze = bool(ctx.attention_events)
        assessment_confidence = (
            min(len(score_components) / 3, 1.0) if has_gaze
            else min(len(score_components) / 3, 0.5)
        )

        return MetricResult(
            name=self.name,
            score=final_score,
            level=score_to_level(final_score),
            confidence=round(assessment_confidence, 2),
            evidence=evidence,
            explanation=(
                f"Attention assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(AttentionMetric())
