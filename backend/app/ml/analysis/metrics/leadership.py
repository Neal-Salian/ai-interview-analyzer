"""
Leadership metric plugin.

Detects leadership indicators from transcript content and behavioral signals.

Signals:
  - Leadership keyword frequency in transcript
  - Assertive communication patterns (decisive language)
  - Initiative indicators (proactive language)
  - Team-oriented framing (leading others, delegating)
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class LeadershipMetric:
    name = "Leadership"
    description = (
        "Detects leadership indicators from the candidate's language, "
        "including initiative, decisiveness, and team-oriented framing."
    )
    version = "1.0"

    LEADERSHIP_KEYWORDS = [
        "led", "lead", "leading", "managed", "directed", "oversaw",
        "mentored", "coached", "delegated", "drove", "championed",
        "spearheaded", "initiated", "founded", "established",
        "influenced", "inspired", "motivated", "empowered",
        "orchestrated", "coordinated", "supervised",
    ]

    INITIATIVE_KEYWORDS = [
        "proposed", "suggested", "volunteered", "started", "launched",
        "created", "built", "introduced", "pioneered", "identified",
        "recognized", "took the initiative", "stepped up",
    ]

    DECISIVE_KEYWORDS = [
        "decided", "chose", "determined", "committed", "prioritized",
        "resolved", "concluded", "selected", "opted", "went with",
    ]

    def compute(self, ctx: SessionContext) -> MetricResult:
        signals: list[str] = []
        evidence: list[dict] = []
        score_components: list[int] = []

        if not ctx.full_transcript or not ctx.full_transcript.strip():
            return MetricResult(
                name=self.name,
                score=0,
                level="Unavailable",
                confidence=0.0,
                evidence=[],
                explanation="No transcript data available.",
                signals_used=[],
            )

        text_lower = ctx.full_transcript.lower()
        word_count = max(len(text_lower.split()), 1)

        # ── Signal 1: Leadership keywords ────────────────────────────────
        leadership_hits = sum(
            text_lower.count(kw) for kw in self.LEADERSHIP_KEYWORDS
        )
        # Normalize per 100 words, cap at 100
        leadership_density = (leadership_hits / word_count) * 100
        leadership_score = int(min(leadership_density * 20, 100))
        score_components.append(max(0, min(100, leadership_score)))
        signals.append("leadership_language")

        if leadership_hits > 0:
            evidence.append({
                "quote": f"Used {leadership_hits} leadership-related term(s) across the interview",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 2: Initiative language ────────────────────────────────
        initiative_hits = sum(
            text_lower.count(kw) for kw in self.INITIATIVE_KEYWORDS
        )
        initiative_density = (initiative_hits / word_count) * 100
        initiative_score = int(min(initiative_density * 25, 100))
        score_components.append(max(0, min(100, initiative_score)))
        signals.append("initiative_language")

        # ── Signal 3: Decisive language ──────────────────────────────────
        decisive_hits = sum(
            text_lower.count(kw) for kw in self.DECISIVE_KEYWORDS
        )
        decisive_density = (decisive_hits / word_count) * 100
        decisive_score = int(min(decisive_density * 30, 100))
        score_components.append(max(0, min(100, decisive_score)))
        signals.append("decisiveness")

        # ── Signal 4: Confident delivery ─────────────────────────────────
        if ctx.emotions:
            # Leaders tend to show more positive emotions
            positive_count = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") in {"happy", "surprise"}
            )
            neutral_count = sum(
                1 for e in ctx.emotions
                if e.get("dominant_emotion") == "neutral"
            )
            composed_ratio = (positive_count + neutral_count) / len(ctx.emotions)
            delivery_score = int(composed_ratio * 100)
            score_components.append(max(0, min(100, delivery_score)))
            signals.append("confident_delivery")

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
                f"Leadership assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(LeadershipMetric())
