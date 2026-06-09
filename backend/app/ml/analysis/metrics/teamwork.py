"""
Teamwork metric plugin.

Detects teamwork and collaboration indicators from transcript content.

Signals:
  - Collaboration keyword frequency
  - Team-oriented framing (we vs I ratio)
  - Conflict resolution language
  - Empathy and support indicators
"""

from app.ml.analysis.interfaces import (
    MetricResult, SessionContext, score_to_level,
)
from app.ml.analysis.registry import register_metric


class TeamworkMetric:
    name = "Teamwork"
    description = (
        "Detects collaboration and teamwork indicators from the candidate's "
        "language, including team-oriented framing and interpersonal skills."
    )
    version = "1.0"

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
        words = text_lower.split()
        word_count = max(len(words), 1)

        # ── Signal 1: Collaboration keywords ─────────────────────────────
        collab_hits = sum(
            text_lower.count(kw) for kw in self.COLLABORATION_KEYWORDS
        )
        collab_density = (collab_hits / word_count) * 100
        collab_score = int(min(collab_density * 15, 100))
        score_components.append(max(0, min(100, collab_score)))
        signals.append("collaboration_language")

        if collab_hits > 0:
            evidence.append({
                "quote": f"Used {collab_hits} collaboration-related term(s) across the interview",
                "timestamp": "",
                "source": "transcript_analysis",
            })

        # ── Signal 2: We vs I ratio ──────────────────────────────────────
        we_count = sum(1 for w in words if w in ("we", "we've", "our", "us"))
        i_count = sum(1 for w in words if w in ("i", "i've", "i'd", "my", "me"))
        total_pronouns = we_count + i_count

        if total_pronouns > 0:
            we_ratio = we_count / total_pronouns
            # Higher "we" ratio = more team-oriented
            # But some "I" is expected — perfect balance is ~40% we
            if we_ratio >= 0.3:
                pronoun_score = int(min(we_ratio * 120, 100))
            else:
                pronoun_score = int(we_ratio * 200)  # low we → lower score
            score_components.append(max(0, min(100, pronoun_score)))
            signals.append("team_oriented_framing")

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
        conflict_density = (conflict_hits / word_count) * 100
        conflict_score = int(min(conflict_density * 40, 100))
        score_components.append(max(0, min(100, conflict_score)))
        signals.append("conflict_resolution")

        # ── Signal 4: Empathy indicators ─────────────────────────────────
        empathy_hits = sum(
            text_lower.count(kw) for kw in self.EMPATHY_KEYWORDS
        )
        empathy_density = (empathy_hits / word_count) * 100
        empathy_score = int(min(empathy_density * 30, 100))
        score_components.append(max(0, min(100, empathy_score)))
        signals.append("empathy_indicators")

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
                f"Teamwork assessed using {len(score_components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
        )


# Auto-register on import
register_metric(TeamworkMetric())
