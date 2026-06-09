"""
Adaptability metric plugin.

Detects adaptability and flexibility indicators from transcript content.

Signals:
  - Adaptability keyword frequency
  - Problem-solving language patterns
  - Growth mindset indicators
  - Emotional resilience under challenging questions
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class AdaptabilityMetric:
    name = "Adaptability"
    description = (
        "Detects adaptability and flexibility indicators from the candidate's "
        "language, including problem-solving ability and growth mindset."
    )
    version = "1.0"

    ADAPTABILITY_KEYWORDS = [
        "adapted", "adjusted", "pivoted", "flexible", "changed",
        "shifted", "transitioned", "evolved", "iterated", "modified",
        "restructured", "revised", "accommodated", "dynamic",
        "agile", "responsive", "versatile",
    ]

    PROBLEM_SOLVING_KEYWORDS = [
        "solved", "solution", "figured out", "troubleshot", "debugged",
        "diagnosed", "analyzed", "investigated", "root cause",
        "workaround", "alternative", "approach", "strategy",
        "brainstormed", "experimented",
    ]

    GROWTH_MINDSET_KEYWORDS = [
        "learned", "learning", "grew", "growth", "improved",
        "feedback", "mistake", "lesson", "developed", "evolved",
        "upskilled", "training", "curious", "explored", "discovered",
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

        # ── Signal 1: Adaptability keywords ──────────────────────────────
        adapt_hits = sum(
            text_lower.count(kw) for kw in self.ADAPTABILITY_KEYWORDS
        )
        adapt_density = (adapt_hits / word_count) * 100
        adapt_score = int(min(adapt_density * 20, 100))
        score_components.append(max(0, min(100, adapt_score)))
        signals.append("adaptability_language")

        if adapt_hits > 0:
            evidence.append({
                "quote": f"Used {adapt_hits} adaptability-related term(s) across the interview",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 2: Problem-solving language ───────────────────────────
        problem_hits = sum(
            text_lower.count(kw) for kw in self.PROBLEM_SOLVING_KEYWORDS
        )
        problem_density = (problem_hits / word_count) * 100
        problem_score = int(min(problem_density * 20, 100))
        score_components.append(max(0, min(100, problem_score)))
        signals.append("problem_solving_language")

        if problem_hits > 2:
            evidence.append({
                "quote": f"Demonstrated problem-solving language with {problem_hits} relevant terms",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 3: Growth mindset indicators ──────────────────────────
        growth_hits = sum(
            text_lower.count(kw) for kw in self.GROWTH_MINDSET_KEYWORDS
        )
        growth_density = (growth_hits / word_count) * 100
        growth_score = int(min(growth_density * 20, 100))
        score_components.append(max(0, min(100, growth_score)))
        signals.append("growth_mindset")

        if growth_hits > 2:
            evidence.append({
                "quote": f"Showed growth mindset with {growth_hits} learning-oriented terms",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 4: Emotional resilience ───────────────────────────────
        # Candidates who stay composed during challenging moments
        # show adaptability
        if ctx.emotions and len(ctx.emotions) >= 5:
            negative_emotions = {"angry", "fear", "sad", "disgust"}
            # Check the second half of the interview
            # (where pressure questions typically come)
            mid = len(ctx.emotions) // 2
            second_half = ctx.emotions[mid:]
            neg_in_second = sum(
                1 for e in second_half
                if e.get("dominant_emotion") in negative_emotions
            )
            neg_ratio_second = neg_in_second / max(len(second_half), 1)
            resilience_score = int((1 - neg_ratio_second) * 100)
            score_components.append(max(0, min(100, resilience_score)))
            signals.append("emotional_resilience")

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
                f"Adaptability assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(AdaptabilityMetric())
