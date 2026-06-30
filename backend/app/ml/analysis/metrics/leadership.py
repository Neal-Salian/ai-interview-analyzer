"""
Leadership metric plugin.

Detects leadership indicators from transcript content and behavioral signals.

Signals:
  - Leadership keyword frequency in transcript
  - Assertive communication patterns (decisive language)
  - Initiative indicators (proactive language)
  - Team-oriented framing (leading others, delegating)

v2.0: Confidence-weighted scoring with keyword-density confidence,
      minimum word-count guards, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import MetricResult, SessionContext
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    keyword_density_confidence,
    score_to_level,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class LeadershipMetric:
    name = "Leadership"
    description = (
        "Detects leadership indicators from the candidate's language, "
        "including initiative, decisiveness, and team-oriented framing."
    )
    version = "2.0"

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

    # Minimum data thresholds
    MIN_TRANSCRIPT_WORDS = 100
    IDEAL_TRANSCRIPT_WORDS = 300
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        if not ctx.candidate_transcript or not ctx.candidate_transcript.strip():
            return MetricResult(
                name=self.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                confidence_details=[],
                evidence=[],
                explanation="No transcript data available.",
                signals_used=[],
            )

        text_lower = ctx.candidate_transcript.lower()
        word_count = max(len(text_lower.split()), 1)

        # ── Signal 1: Leadership keywords ────────────────────────────────
        leadership_hits = sum(
            text_lower.count(kw) for kw in self.LEADERSHIP_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=leadership_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            leadership_density = (leadership_hits / word_count) * 100
            leadership_score = int(min(leadership_density * 20, 100))

            components.append(SignalComponent(
                score=max(0, min(100, leadership_score)),
                confidence=sig_confidence,
                signal_name="leadership_language",
            ))

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
        sig_confidence = keyword_density_confidence(
            hits=initiative_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            initiative_density = (initiative_hits / word_count) * 100
            initiative_score = int(min(initiative_density * 25, 100))

            components.append(SignalComponent(
                score=max(0, min(100, initiative_score)),
                confidence=sig_confidence,
                signal_name="initiative_language",
            ))

        # ── Signal 3: Decisive language ──────────────────────────────────
        decisive_hits = sum(
            text_lower.count(kw) for kw in self.DECISIVE_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=decisive_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            decisive_density = (decisive_hits / word_count) * 100
            decisive_score = int(min(decisive_density * 30, 100))

            components.append(SignalComponent(
                score=max(0, min(100, decisive_score)),
                confidence=sig_confidence,
                signal_name="decisiveness",
            ))

        # ── Signal 4: Confident delivery ─────────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                # Leaders tend to show more positive emotions
                positive_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in {"happy", "surprise"}
                )
                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                composed_ratio = (positive_count + neutral_count) / n
                delivery_score = int(composed_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, delivery_score)),
                    confidence=sig_confidence,
                    signal_name="confident_delivery",
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
                explanation="Insufficient data to assess leadership.",
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
                f"Leadership assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(LeadershipMetric())
