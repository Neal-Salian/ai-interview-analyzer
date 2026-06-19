"""
Teamwork metric plugin.

Detects teamwork and collaboration indicators from transcript content.

Signals:
  - Collaboration keyword frequency
  - Team-oriented framing (we vs I ratio)
  - Conflict resolution language
  - Empathy and support indicators

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


class TeamworkMetric:
    name = "Teamwork"
    description = (
        "Detects collaboration and teamwork indicators from the candidate's "
        "language, including team-oriented framing and interpersonal skills."
    )
    version = "2.0"

    COLLABORATION_KEYWORDS = [
        "team", "together", "collaborate", "collaborated", "partnership",
        "collective", "group", "joint", "shared", "contributed",
        "supported", "helped", "assisted", "worked with",
        "cross-functional", "stakeholders", "peers",
    ]

    CONFLICT_RESOLUTION_KEYWORDS = [
        "resolved", "mediated", "compromise", "consensus", "aligned",
        "negotiated", "addressed", "discussed", "reconciled",
        "found common ground", "de-escalated",
    ]

    EMPATHY_KEYWORDS = [
        "understood", "listened", "empathize", "perspective", "appreciated",
        "acknowledged", "respected", "considered", "inclusive", "supported",
        "encouraged", "recognized their",
    ]

    # Minimum data thresholds
    MIN_TRANSCRIPT_WORDS = 100
    IDEAL_TRANSCRIPT_WORDS = 300

    def compute(self, ctx: SessionContext) -> MetricResult:
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        if not ctx.full_transcript or not ctx.full_transcript.strip():
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

        text_lower = ctx.full_transcript.lower()
        words = text_lower.split()
        word_count = max(len(words), 1)

        # ── Signal 1: Collaboration keywords ─────────────────────────────
        collab_hits = sum(
            text_lower.count(kw) for kw in self.COLLABORATION_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=collab_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            collab_density = (collab_hits / word_count) * 100
            collab_score = int(min(collab_density * 15, 100))

            components.append(SignalComponent(
                score=max(0, min(100, collab_score)),
                confidence=sig_confidence,
                signal_name="collaboration_language",
            ))

            if collab_hits > 0:
                evidence.append({
                    "quote": f"Used {collab_hits} collaboration-related term(s) across the interview",
                    "timestamp": "",
                    "source": "transcript_analysis",
                })

        # ── Signal 2: We vs I ratio ──────────────────────────────────────
        # Require minimum word count for pronoun analysis to be meaningful
        pronoun_confidence = sample_size_confidence(
            word_count, self.MIN_TRANSCRIPT_WORDS, self.IDEAL_TRANSCRIPT_WORDS
        )
        if pronoun_confidence > 0:
            we_count = sum(1 for w in words if w in ("we", "we've", "our", "us"))
            i_count = sum(1 for w in words if w in ("i", "i've", "i'd", "my", "me"))
            total_pronouns = we_count + i_count

            if total_pronouns > 0:
                we_ratio = we_count / total_pronouns
                # Higher "we" ratio = more team-oriented
                if we_ratio >= 0.3:
                    pronoun_score = int(min(we_ratio * 120, 100))
                else:
                    pronoun_score = int(we_ratio * 200)

                # Confidence also scales with total pronoun count
                pronoun_sig_confidence = min(
                    pronoun_confidence,
                    sample_size_confidence(total_pronouns, 5, 20),
                )
                if pronoun_sig_confidence >= 0.1:
                    components.append(SignalComponent(
                        score=max(0, min(100, pronoun_score)),
                        confidence=pronoun_sig_confidence,
                        signal_name="team_oriented_framing",
                    ))

                    if we_ratio > 0.4:
                        evidence.append({
                            "quote": f'Used "we/our/us" {we_count} times vs "I/my/me" {i_count} times (team-oriented framing)',
                            "timestamp": "",
                            "source": "transcript_analysis",
                        })

        # ── Signal 3: Conflict resolution language ───────────────────────
        conflict_hits = sum(
            text_lower.count(kw) for kw in self.CONFLICT_RESOLUTION_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=conflict_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            conflict_density = (conflict_hits / word_count) * 100
            conflict_score = int(min(conflict_density * 40, 100))

            components.append(SignalComponent(
                score=max(0, min(100, conflict_score)),
                confidence=sig_confidence,
                signal_name="conflict_resolution",
            ))

        # ── Signal 4: Empathy indicators ─────────────────────────────────
        empathy_hits = sum(
            text_lower.count(kw) for kw in self.EMPATHY_KEYWORDS
        )
        sig_confidence = keyword_density_confidence(
            hits=empathy_hits,
            word_count=word_count,
            min_words=self.MIN_TRANSCRIPT_WORDS,
            ideal_words=self.IDEAL_TRANSCRIPT_WORDS,
        )
        if sig_confidence > 0:
            empathy_density = (empathy_hits / word_count) * 100
            empathy_score = int(min(empathy_density * 30, 100))

            components.append(SignalComponent(
                score=max(0, min(100, empathy_score)),
                confidence=sig_confidence,
                signal_name="empathy_indicators",
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
                explanation="Insufficient data to assess teamwork.",
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
                f"Teamwork assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}. "
                f"Weighted score: {result['final_score']}, "
                f"unweighted: {result['raw_score']}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(TeamworkMetric())
