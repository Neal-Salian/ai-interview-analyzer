"""
Engagement metric plugin.

Assesses candidate engagement based on:
  - Eye contact percentage (attention data)
  - Emotional expressiveness (emotion variety vs. flat neutral)
  - Response elaboration (transcript length relative to questions)
  - Question relevance (did answers address the asked questions)

v2.0: Confidence-weighted scoring with sample-size guards and
      per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import MetricResult, SessionContext
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    score_to_level,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class EngagementMetric:
    name = "Engagement"
    description = (
        "Measures how actively the candidate participates in the interview "
        "through eye contact, emotional expressiveness, and response depth."
    )
    version = "2.0"

    # Minimum data thresholds
    MIN_ATTENTION_EVENTS = 5
    IDEAL_ATTENTION_EVENTS = 30
    MIN_EMOTION_FRAMES = 10
    IDEAL_EMOTION_FRAMES = 50
    MIN_TRANSCRIPT_CHUNKS = 3
    IDEAL_TRANSCRIPT_CHUNKS = 15
    MIN_QUESTIONS = 3
    IDEAL_QUESTIONS = 8

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        # ── Signal 1: Eye contact (attention data) ───────────────────────
        if ctx.attention_events:
            n = len(ctx.attention_events)
            sig_confidence = sample_size_confidence(
                n, self.MIN_ATTENTION_EVENTS, self.IDEAL_ATTENTION_EVENTS
            )
            if sig_confidence > 0:
                total = n
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

                components.append(SignalComponent(
                    score=max(0, min(100, eye_score)),
                    confidence=sig_confidence,
                    signal_name="eye_contact_ratio",
                ))

                if engaged_ratio < 0.5:
                    evidence.append({
                        "quote": f"Candidate maintained direct eye contact {engaged_ratio:.0%} of the time",
                        "timestamp": "",
                        "source": "attention_tracking",
                    })

        # ── Signal 2: Emotional expressiveness ───────────────────────────
        if ctx.emotions:
            n = len(ctx.emotions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_EMOTION_FRAMES, self.IDEAL_EMOTION_FRAMES
            )
            if sig_confidence > 0:
                unique_emotions = set(
                    e.get("dominant_emotion") for e in ctx.emotions
                )
                # Scale variety score by sample size — 3 emotions in 10 frames
                # is less meaningful than 3 emotions in 100 frames
                raw_variety = min(len(unique_emotions) * 20, 100)
                # Dampen variety score for small samples
                variety_score = int(raw_variety * min(n / 20, 1.0))

                # Check neutral dominance
                neutral_count = sum(
                    1 for e in ctx.emotions
                    if e.get("dominant_emotion") == "neutral"
                )
                neutral_ratio = neutral_count / n
                # Heavily neutral = lower engagement
                expression_score = int(
                    variety_score * 0.4 + (1 - neutral_ratio) * 100 * 0.6
                )

                components.append(SignalComponent(
                    score=max(0, min(100, expression_score)),
                    confidence=sig_confidence,
                    signal_name="emotional_expressiveness",
                ))

        # ── Signal 3: Response depth ─────────────────────────────────────
        if ctx.transcripts:
            n = len(ctx.transcripts)
            sig_confidence = sample_size_confidence(
                n, self.MIN_TRANSCRIPT_CHUNKS, self.IDEAL_TRANSCRIPT_CHUNKS
            )
            if sig_confidence > 0:
                avg_length = sum(
                    len(t.get("text", "").split()) for t in ctx.transcripts
                ) / max(n, 1)

                # Average 30+ words per chunk is good engagement
                depth_score = int(min(avg_length / 30 * 100, 100))

                components.append(SignalComponent(
                    score=max(0, min(100, depth_score)),
                    confidence=sig_confidence,
                    signal_name="response_depth",
                ))

                if avg_length < 15:
                    evidence.append({
                        "quote": f"Average response length was {avg_length:.0f} words per chunk (brief responses)",
                        "timestamp": "",
                        "source": "transcript_analysis",
                    })

        # ── Signal 4: Question interaction ───────────────────────────────
        if ctx.questions:
            n = len(ctx.questions)
            sig_confidence = sample_size_confidence(
                n, self.MIN_QUESTIONS, self.IDEAL_QUESTIONS
            )
            if sig_confidence > 0:
                asked = [q for q in ctx.questions if q.get("was_asked")]
                if asked:
                    ask_ratio = len(asked) / n
                    question_score = int(ask_ratio * 100)

                    components.append(SignalComponent(
                        score=max(0, min(100, question_score)),
                        confidence=sig_confidence,
                        signal_name="question_interaction",
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
                explanation="Insufficient data to assess engagement.",
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
                f"Engagement assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(EngagementMetric())
