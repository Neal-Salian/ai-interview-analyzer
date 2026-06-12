"""
Communication effectiveness metric plugin.

Assesses how effectively the candidate communicates.

Signals:
  - Vocabulary diversity (unique word ratio)
  - Response coherence (average words per response)
  - STAR structure usage (Situation, Task, Action, Result keywords)
  - Speaking pace (words per transcript chunk)
  - Sentiment consistency (stable positive tone)
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class CommunicationMetric:
    name = "Communication"
    description = (
        "Evaluates communication effectiveness including vocabulary diversity, "
        "response structure, and speaking clarity."
    )
    version = "1.0"

    STAR_KEYWORDS = {
        "situation": ["situation", "context", "background", "scenario", "when"],
        "task": ["task", "goal", "objective", "challenge", "needed to", "had to", "responsible"],
        "action": ["action", "decided", "implemented", "built", "created", "designed", "led", "developed"],
        "result": ["result", "outcome", "achieved", "improved", "reduced", "increased", "delivered", "impact"],
    }

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

        words = ctx.full_transcript.lower().split()
        word_count = max(len(words), 1)

        # ── Signal 1: Vocabulary diversity ───────────────────────────────
        unique_words = set(words)
        diversity_ratio = len(unique_words) / word_count
        # Good diversity is around 0.4-0.6 for spoken language
        diversity_score = int(min(diversity_ratio * 200, 100))
        score_components.append(max(0, min(100, diversity_score)))
        signals.append("vocabulary_diversity")

        if diversity_ratio < 0.25:
            evidence.append({
                "quote": f"Vocabulary diversity ratio: {diversity_ratio:.2f} (limited word variety)",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 2: Response coherence (words per chunk) ───────────────
        if ctx.transcripts and len(ctx.transcripts) >= 2:
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
                score_components.append(max(0, min(100, coherence_score)))
                signals.append("response_coherence")

        # ── Signal 3: STAR structure ─────────────────────────────────────
        text_lower = ctx.full_transcript.lower()
        star_hits = {}
        for component, keywords in self.STAR_KEYWORDS.items():
            star_hits[component] = sum(
                text_lower.count(kw) for kw in keywords
            )

        components_present = sum(1 for v in star_hits.values() if v > 0)
        # 4/4 STAR components → 100, 3/4 → 75, etc.
        star_score = int((components_present / 4) * 100)
        score_components.append(star_score)
        signals.append("star_structure")

        if components_present >= 3:
            evidence.append({
                "quote": f"Candidate used {components_present}/4 STAR framework components in responses",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 4: Sentiment consistency ──────────────────────────────
        if ctx.emotions and len(ctx.emotions) >= 5:
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
            stable_ratio = (positive_count + neutral_count) / len(ctx.emotions)
            tone_score = int(stable_ratio * 100)
            score_components.append(max(0, min(100, tone_score)))
            signals.append("communication_tone")

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
                f"Communication assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(CommunicationMetric())
