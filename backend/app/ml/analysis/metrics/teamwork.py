"""
Teamwork metric plugin — Enterprise Competency Framework.

Detects teamwork and collaboration indicators from transcript content.

V3.0: Evidence-first evaluation. When structured evidence is available
(from the preprocessing pipeline), the plugin scores pre-extracted
teamwork behaviours (e.g., collaboration, conflict resolution).
Falls back to keyword-based analysis when evidence is unavailable.

v2.0: Confidence-weighted scoring with keyword-density confidence,
      minimum word-count guards, and per-signal confidence breakdown.
"""

from app.ml.analysis.interfaces import (
    MetricResult,
    EnhancedMetricResult,
    SessionContext,
)
from app.ml.analysis.scoring_utils import (
    confidence_weighted_average,
    sample_size_confidence,
    keyword_density_confidence,
    score_to_level,
    evidence_based_confidence,
    SignalComponent,
)
from app.ml.analysis.registry import register_metric


class TeamworkMetric:
    name = "Teamwork"
    description = (
        "Detects collaboration and teamwork indicators from the candidate's "
        "language, including team-oriented framing and interpersonal skills."
    )
    version = "3.0"
    author = "Platform Team"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {"category": "competency", "tier": "core"}

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
        # ── Try evidence-based evaluation first ───────────────────────────
        evidence = getattr(ctx, "evidence", None)
        if evidence and not evidence.is_empty():
            rel_types = ["collaboration", "teamwork", "conflict_resolution", "empathy"]
            behaviours = []
            for t in rel_types:
                behaviours.extend(evidence.get_behaviours_by_type(t))
            
            if behaviours:
                return self._evidence_based_compute(ctx, evidence, behaviours)

        # ── Fallback: keyword-based evaluation (V2 logic) ────────────────
        return self._keyword_based_compute(ctx)

    def _evidence_based_compute(
        self, ctx: SessionContext, evidence, behaviours
    ) -> EnhancedMetricResult:
        """Score teamwork using pre-extracted behaviour evidence."""
        components: list[SignalComponent] = []
        sub_dimensions: list[dict] = []
        evidence_ids: list[str] = []
        transcript_refs: list[str] = []

        avg_confidence = sum(b.confidence for b in behaviours) / len(behaviours)
        base_score = min(int(len(behaviours) * 20 + avg_confidence * 20), 100)

        components.append(SignalComponent(
            score=max(0, min(100, base_score)),
            confidence=avg_confidence,
            signal_name="teamwork_behaviours",
        ))

        # Track evidence
        for b in behaviours:
            evidence_ids.append(b.id)
            if b.transcript_reference:
                transcript_refs.append(b.transcript_reference)

        # ── Aggregate ─────────────────────────────────────────────────────
        result = confidence_weighted_average(components)
        signals = [c["signal_name"] for c in components]

        types_found = set(b.behaviour_type for b in behaviours)
        reasoning_parts = [
            f"Observed collaborative behaviours: {', '.join(types_found)}."
        ]
        
        recommendations = []
        if result["final_score"] >= 70:
            recommendations.append(
                "Strong collaborative orientation. Likely a good fit for highly cross-functional teams."
            )
        else:
            recommendations.append(
                "Limited collaboration indicators. Assess interpersonal dynamics in follow-up."
            )

        return EnhancedMetricResult(
            name=self.name,
            score=result["final_score"],
            raw_score=result["raw_score"],
            level=score_to_level(result["final_score"]),
            confidence=result["overall_confidence"],
            confidence_details=result["confidence_details"],
            evidence=[{"source": "evidence_pipeline", "count": len(behaviours)}],
            explanation=(
                f"Teamwork assessed using {len(components)} signal(s): "
                f"{', '.join(signals)}."
            ),
            signals_used=signals,
            summary=(
                f"Interview evidence suggests "
                f"{'strong' if result['final_score'] >= 70 else 'moderate'} "
                f"collaboration and teamwork skills."
            ),
            reasoning=" ".join(reasoning_parts),
            recommendations=recommendations,
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            sub_dimensions=sub_dimensions,
            metadata=self.plugin_metadata,
        )

    def _keyword_based_compute(self, ctx: SessionContext) -> MetricResult:
        """V2 keyword-based fallback logic."""
        components: list[SignalComponent] = []
        evidence: list[dict] = []

        transcript = getattr(ctx, "candidate_transcript", "") or ctx.full_transcript
        if not transcript or not transcript.strip():
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

        text_lower = transcript.lower()
        words = text_lower.split()
        word_count = max(len(words), 1)

        # ── Signal 1: Collaboration keywords ─────────────────────────────
        collab_hits = sum(text_lower.count(kw) for kw in self.COLLABORATION_KEYWORDS)
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
        pronoun_confidence = sample_size_confidence(
            word_count, self.MIN_TRANSCRIPT_WORDS, self.IDEAL_TRANSCRIPT_WORDS
        )
        if pronoun_confidence > 0:
            we_count = sum(1 for w in words if w in ("we", "we've", "our", "us"))
            i_count = sum(1 for w in words if w in ("i", "i've", "i'd", "my", "me"))
            total_pronouns = we_count + i_count

            if total_pronouns > 0:
                we_ratio = we_count / total_pronouns
                if we_ratio >= 0.3:
                    pronoun_score = int(min(we_ratio * 120, 100))
                else:
                    pronoun_score = int(we_ratio * 200)

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
                            "quote": f'Used "we/our/us" {we_count} times vs "I/my/me" {i_count} times',
                            "timestamp": "",
                            "source": "transcript_analysis",
                        })

        # ── Signal 3: Conflict resolution language ───────────────────────
        conflict_hits = sum(text_lower.count(kw) for kw in self.CONFLICT_RESOLUTION_KEYWORDS)
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
        empathy_hits = sum(text_lower.count(kw) for kw in self.EMPATHY_KEYWORDS)
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
