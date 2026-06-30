"""
Adaptability metric plugin.

Detects adaptability and flexibility indicators from transcript content.

Signals:
  - Adaptability keyword frequency
  - Problem-solving language patterns
  - Growth mindset indicators
  - Emotional resilience under challenging questions

v2.0: Confidence-weighted scoring with keyword-density confidence,
      raised sample-size thresholds, and per-signal confidence breakdown.
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


class AdaptabilityMetric:
    name = "Adaptability"
    description = (
        "Detects adaptability and flexibility indicators from the candidate's "
        "language, including problem-solving ability and growth mindset."
    )
    version = "2.0"

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

        # ── Signal 1: Adaptability keywords ──────────────────────────────
        adapt_hits = sum(
            text_lower.count(kw) for kw in self.ADAPTABILITY_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=adapt_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            adapt_density = (adapt_hits / word_count) * 100
            adapt_score = int(min(adapt_density * 20, 100))

            components.append(SignalComponent(
                score=max(0, min(100, adapt_score)),
                confidence=sig_confidence,
                signal_name="adaptability_language",
            ))

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
        sig_confidence = keyword_density_confidence(
            hits=problem_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            problem_density = (problem_hits / word_count) * 100
            problem_score = int(min(problem_density * 20, 100))

            components.append(SignalComponent(
                score=max(0, min(100, problem_score)),
                confidence=sig_confidence,
                signal_name="problem_solving_language",
            ))

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
        sig_confidence = keyword_density_confidence(
            hits=growth_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            growth_density = (growth_hits / word_count) * 100
            growth_score = int(min(growth_density * 20, 100))

            components.append(SignalComponent(
                score=max(0, min(100, growth_score)),
                confidence=sig_confidence,
                signal_name="growth_mindset",
            ))

            if growth_hits > 2:
                evidence.append({
                    "quote": f"Showed growth mindset with {growth_hits} learning-oriented terms",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 4: Emotional resilience ───────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                negative_emotions = {"angry", "fear", "sad", "disgust"}
                # Check the second half of the interview
                mid = n // 2
                second_half = ctx.emotions[mid:]
                neg_in_second = sum(
                    1 for e in second_half
                    if e.get("dominant_emotion") in negative_emotions
                )
                neg_ratio_second = neg_in_second / max(len(second_half), 1)
                resilience_score = int((1 - neg_ratio_second) * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, resilience_score)),
                    confidence=sig_confidence,
                    signal_name="emotional_resilience",
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
                explanation="Insufficient data to assess adaptability.",
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
                f"Adaptability assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(AdaptabilityMetric())
