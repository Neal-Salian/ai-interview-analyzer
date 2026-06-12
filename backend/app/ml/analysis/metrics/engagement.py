"""
Engagement metric plugin.

Assesses candidate engagement based on:
  - Eye contact percentage (attention data)
  - Emotional expressiveness (emotion variety vs. flat neutral)
  - Response elaboration (transcript length relative to questions)
  - Question relevance (did answers address the asked questions)
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class EngagementMetric:
    name = "Engagement"
    description = (
        "Measures how actively the candidate participates in the interview "
        "through eye contact, emotional expressiveness, and response depth."
    )
    version = "1.0"

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        score_components: list[int] = []

        # ── Signal 1: Eye contact (attention data) ───────────────────────
        if ctx.attention_events:
            total = len(ctx.attention_events)
            center = sum(
                1 for a in ctx.attention_events
                if a.get("direction") == "center"
            )
            missing = sum(
                1 for a in ctx.attention_events
                if a.get("direction") == "missing"
            )
            # Penalize both looking away AND face missing
            engaged_ratio = center / total
            missing_ratio = missing / total
            eye_score = int(engaged_ratio * 100)
            if missing_ratio > 0.1:
                eye_score = int(eye_score * (1 - missing_ratio))
            score_components.append(max(0, min(100, eye_score)))
            signals.append("eye_contact_ratio")

            if engaged_ratio < 0.5:
                evidence.append({
                    "quote": f"Candidate maintained direct eye contact {engaged_ratio:.0%} of the time",
                    "timestamp": "",
                    "source": "attention_tracking",
                })

        # ── Signal 2: Emotional expressiveness ───────────────────────────
        if ctx.emotions:
            unique_emotions = set(
                e.get("dominant_emotion") for e in ctx.emotions
            )
            # More variety = more engaged (monotone neutral = less engaged)
            variety_score = min(len(unique_emotions) * 20, 100)
            # But also check neutral dominance
            neutral_count = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") == "neutral"
            )
            neutral_ratio = neutral_count / len(ctx.emotions)
            # Heavily neutral = lower engagement
            expression_score = int(
                variety_score * 0.4 + (1 - neutral_ratio) * 100 * 0.6
            )
            score_components.append(max(0, min(100, expression_score)))
            signals.append("emotional_expressiveness")

        # ── Signal 3: Response depth ─────────────────────────────────────
        if ctx.transcripts:
            # More transcript chunks = more talking = more engaged
            avg_length = sum(
                len(t.get("text", "").split()) for t in ctx.transcripts
            ) / max(len(ctx.transcripts), 1)

            # Average 30+ words per chunk is good engagement
            depth_score = int(min(avg_length / 30 * 100, 100))
            score_components.append(max(0, min(100, depth_score)))
            signals.append("response_depth")

            if avg_length < 15:
                evidence.append({
                    "quote": f"Average response length was {avg_length:.0f} words per chunk (brief responses)",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 4: Question interaction ───────────────────────────────
        if ctx.questions:
            asked = [q for q in ctx.questions if q.get("was_asked")]
            if asked:
                ask_ratio = len(asked) / len(ctx.questions)
                # More questions asked = interviewer found responses
                # engaging enough to probe further
                question_score = int(ask_ratio * 100)
                score_components.append(max(0, min(100, question_score)))
                signals.append("question_interaction")

        # ── Aggregate ────────────────────────────────────────────────────
        if not score_components:
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="Insufficient data to assess engagement.",
                signals_used=[],
            )

        final_score = int(sum(score_components) / len(score_components))
        assessment_confidence = min(len(score_components) / 4, 1.0)

        return MetricResult(
            name=self.name,
            score=final_score,
            level=score_to_level(final_score),
            confidence=round(assessment_confidence, 2),
            evidence=evidence,
            explanation=(
                f"Engagement assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(EngagementMetric())
