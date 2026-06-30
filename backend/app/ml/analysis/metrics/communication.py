"""
Communication effectiveness metric plugin.

Assesses how effectively the candidate communicates.

Signals:
  - Vocabulary diversity (unique word ratio)
  - Response coherence (average words per response)
  - STAR structure usage (Situation, Task, Action, Result keywords)
  - Sentiment consistency (stable positive tone)

v2.0: Confidence-weighted scoring with sample-size guards, keyword-density
      confidence, and per-signal confidence breakdown.
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


class CommunicationMetric:
    name = "Communication"
    description = (
        "Evaluates communication effectiveness including vocabulary diversity, "
        "response structure, and speaking clarity."
    )
    version = "2.0"

    STAR_KEYWORDS = {
        "situation": ["situation", "context", "background", "scenario", "when"],
        "task": ["task", "goal", "objective", "challenge", "needed to", "had to", "responsible"],
        "action": ["action", "decided", "implemented", "built", "created", "designed", "led", "developed"],
        "result": ["result", "outcome", "achieved", "improved", "reduced", "increased", "delivered", "impact"],
    }

    # Minimum data thresholds
    MIN_TRANSCRIPT_WORDS = 50
    IDEAL_TRANSCRIPT_WORDS = 200
    MIN_TRANSCRIPT_CHUNKS = 3
    IDEAL_TRANSCRIPT_CHUNKS = 15
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

        words = ctx.candidate_transcript.lower().split()
        word_count = max(len(words), 1)

        # ── Signal 1: Vocabulary diversity ───────────────────────────────
        vocab_confidence = sample_size_confidence(
            word_count, self.MIN_TRANSCRIPT_WORDS, self.IDEAL_TRANSCRIPT_WORDS
        )
        if vocab_confidence > 0:
            unique_words = set(words)
            diversity_ratio = len(unique_words) / word_count
            # Good diversity is around 0.4-0.6 for spoken language
            diversity_score = int(min(diversity_ratio * 200, 100))

            components.append(SignalComponent(
                score=max(0, min(100, diversity_score)),
                confidence=vocab_confidence,
                signal_name="vocabulary_diversity",
            ))

            if diversity_ratio < 0.25:
                evidence.append({
                    "quote": f"Vocabulary diversity ratio: {diversity_ratio:.2f} (limited word variety)",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 2: Response coherence (words per chunk) ───────────────
        if ctx.transcripts:
            n = len(ctx.transcripts)
            chunk_confidence = sample_size_confidence(
                n, self.MIN_TRANSCRIPT_CHUNKS, self.IDEAL_TRANSCRIPT_CHUNKS
            )
            if chunk_confidence > 0:
                chunk_word_counts = [
                    len(t.get("text", "").split()) for t in ctx.transcripts
                    if t.get("text", "").strip()
                ]
                if chunk_word_counts:
                    avg_words = sum(chunk_word_counts) / len(chunk_word_counts)
                    # 20-50 words per chunk is good; too short = terse, too long = rambling
                    if avg_words < 10:
                        coherence_score = int(avg_words * 5)  # very short
                    elif avg_words <= 50:
                        coherence_score = int(min(avg_words * 2, 100))  # good range
                    else:
                        coherence_score = int(max(100 - (avg_words - 50), 40))  # rambling

                    components.append(SignalComponent(
                        score=max(0, min(100, coherence_score)),
                        confidence=chunk_confidence,
                        signal_name="response_coherence",
                    ))

        # ── Signal 3: STAR structure ─────────────────────────────────────
        text_lower = ctx.candidate_transcript.lower()
        total_star_hits = 0
        star_hits = {}
        for component_name, keywords in self.STAR_KEYWORDS.items():
            hits = sum(text_lower.count(kw) for kw in keywords)
            star_hits[component_name] = hits
            total_star_hits += hits

        components_present = sum(1 for v in star_hits.values() if v > 0)
        # STAR confidence: needs sufficient transcript length to be meaningful
        star_confidence = keyword_density_confidence(
            hits=total_star_hits,
            word_count=word_count,
            min_words=100,  # STAR is unreliable on very short transcripts
            ideal_words=300,
        )
        if star_confidence > 0:
            # 4/4 STAR components → 100, 3/4 → 75, etc.
            star_score = int((components_present / 4) * 100)

            components.append(SignalComponent(
                score=star_score,
                confidence=star_confidence,
                signal_name="star_structure",
            ))

            if components_present >= 3:
                evidence.append({
                    "quote": f"Candidate used {components_present}/4 STAR framework components in responses",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 4: Sentiment consistency ──────────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            tone_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if tone_confidence > 0:
                positive_emotions = {"happy", "surprise"}
                positive_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") in positive_emotions
                )
                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                # Positive + neutral = stable communicator
                stable_ratio = (positive_count + neutral_count) / n
                tone_score = int(stable_ratio * 100)

                components.append(SignalComponent(
                    score=max(0, min(100, tone_score)),
                    confidence=tone_confidence,
                    signal_name="communication_tone",
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
                explanation="Insufficient data to assess communication.",
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
                f"Communication assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(CommunicationMetric())
