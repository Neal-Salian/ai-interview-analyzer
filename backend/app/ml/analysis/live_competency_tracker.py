"""
Live Competency Evidence Tracker — lightweight, keyword-based runtime tracker.

Tracks competency evidence DURING an interview by scanning each transcript
chunk for competency-relevant keywords.  This is purely an in-memory,
display-only layer — it never calculates final scores, never calls the LLM,
and never writes to the database.

Design:
  - Keyword lists are curated locally (inspired by existing metric plugins)
    but NOT imported from them, to avoid circular imports and plugin coupling.
  - State is per-session, per-competency, stored in a class-level dict.
  - Cleaned up on session teardown via clear().

This module has ZERO coupling to:
  - Evidence Service
  - Scoring Engine
  - Competency Plugins
  - Database layer
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Literal

logger = logging.getLogger(__name__)


# ── Competency keyword definitions ───────────────────────────────────────────
# Each competency has keyword groups.  When keywords from a group are found in
# a transcript chunk, we count it as one observation for that competency and
# record the group name as the observation label.
#
# These are intentionally lightweight — just enough for live progress display.
# Final scoring uses the full evidence service + LLM pipeline at teardown.

COMPETENCY_KEYWORDS: dict[str, dict[str, list[str]]] = {
    "communication": {
        "Structured explanation": [
            "because", "therefore", "for example", "in other words",
            "specifically", "essentially", "to clarify", "the reason",
        ],
        "Clear articulation": [
            "clearly", "articulate", "explain", "describe", "outline",
            "walk you through", "break down", "step by step",
        ],
        "STAR structure usage": [
            "situation", "context", "task", "goal", "objective",
            "action", "decided", "implemented", "result", "outcome",
            "achieved", "improved", "reduced", "increased",
        ],
        "Persuasive communication": [
            "convinced", "persuaded", "advocated", "proposed",
            "recommended", "presented", "pitched", "demonstrated",
        ],
    },
    "leadership": {
        "Took ownership": [
            "led", "lead", "leading", "managed", "directed", "oversaw",
            "owned", "took ownership", "responsible for", "accountable",
        ],
        "Delegated responsibilities": [
            "delegated", "assigned", "empowered", "entrusted",
            "distributed", "coordinated team",
        ],
        "Drove initiative": [
            "initiated", "started", "launched", "proposed", "volunteered",
            "spearheaded", "championed", "pioneered", "introduced",
        ],
        "Strategic decision-making": [
            "decided", "chose", "prioritized", "committed",
            "determined", "resolved", "concluded", "strategy",
        ],
    },
    "teamwork": {
        "Collaborative approach": [
            "team", "together", "collaborate", "collaborated", "partnership",
            "group", "joint", "shared", "worked with", "cross-functional",
        ],
        "Conflict resolution": [
            "resolved", "mediated", "compromise", "consensus", "aligned",
            "negotiated", "found common ground", "de-escalated",
        ],
        "Empathetic engagement": [
            "understood", "listened", "empathize", "perspective",
            "acknowledged", "respected", "inclusive", "supported",
        ],
    },
    "adaptability": {
        "Adapted to change": [
            "adapted", "adjusted", "pivoted", "flexible", "changed",
            "shifted", "transitioned", "evolved", "restructured",
        ],
        "Problem-solving approach": [
            "solved", "solution", "figured out", "troubleshot", "debugged",
            "diagnosed", "analyzed", "root cause", "workaround",
        ],
        "Growth mindset": [
            "learned", "learning", "grew", "growth", "improved",
            "feedback", "mistake", "lesson", "developed", "upskilled",
        ],
    },
    "confidence": {
        "Self-assured response": [
            "confident", "certain", "sure", "absolutely", "definitely",
            "without doubt", "clearly", "strongly believe",
        ],
        "Decisive language": [
            "decided", "chose", "committed", "determined",
            "took the lead", "made the call",
        ],
    },
    "stress_management": {
        "Composure under pressure": [
            "pressure", "deadline", "stressful", "challenge", "crisis",
            "difficult", "setback", "obstacle", "constraint",
        ],
        "Recovery and resilience": [
            "recovered", "bounced back", "overcame", "persevered",
            "resilient", "kept going", "stayed focused", "pushed through",
        ],
    },
}

# Human-friendly display names
COMPETENCY_DISPLAY_NAMES: dict[str, str] = {
    "communication": "Communication",
    "leadership": "Leadership",
    "teamwork": "Teamwork",
    "adaptability": "Adaptability",
    "confidence": "Confidence",
    "stress_management": "Stress Management",
}


# ── LiveCompetencyState ──────────────────────────────────────────────────────

@dataclass
class LiveCompetencyState:
    """Runtime state for a single competency during a live interview."""
    competency_key: str
    display_name: str = ""
    evidence_count: int = 0
    confidence: Literal["Low", "Medium", "High"] = "Low"
    status: Literal["Collecting", "Building", "Ready"] = "Collecting"
    question_ids: list[str] = field(default_factory=list)
    latest_observations: list[str] = field(default_factory=list)

    # Internal: track which observation labels have been seen to avoid duplicates
    _seen_observations: set[str] = field(default_factory=set, repr=False)

    def add_observation(self, observation: str, question_id: str | None = None) -> None:
        """Record a new observation for this competency."""
        if observation in self._seen_observations:
            # Same observation already recorded — just update question if new
            if question_id and question_id not in self.question_ids:
                self.question_ids.append(question_id)
            return

        self._seen_observations.add(observation)
        self.evidence_count += 1

        # Keep latest 3 observations
        self.latest_observations.append(observation)
        if len(self.latest_observations) > 3:
            self.latest_observations = self.latest_observations[-3:]

        if question_id and question_id not in self.question_ids:
            self.question_ids.append(question_id)

        # Update status and confidence based on evidence count
        self._update_levels()

    def _update_levels(self) -> None:
        """Derive status and confidence from evidence_count."""
        if self.evidence_count == 0:
            self.status = "Collecting"
            self.confidence = "Low"
        elif self.evidence_count <= 2:
            self.status = "Building"
            self.confidence = "Medium"
        else:
            self.status = "Ready"
            self.confidence = "High"

    def to_dict(self) -> dict:
        return {
            "competency_key": self.competency_key,
            "display_name": self.display_name,
            "evidence_count": self.evidence_count,
            "confidence": self.confidence,
            "status": self.status,
            "question_ids": list(self.question_ids),
            "latest_observations": list(self.latest_observations),
        }


# ── LiveCompetencyTracker ────────────────────────────────────────────────────

class LiveCompetencyTracker:
    """
    In-memory, per-session competency evidence tracker.

    Class-level state — no database, no LLM, no external I/O.
    Thread-safe for single-process asyncio (the consumer runs on one event loop).
    """
    _sessions: dict[str, dict[str, LiveCompetencyState]] = {}

    @classmethod
    def _ensure_session(cls, session_id: str) -> dict[str, LiveCompetencyState]:
        """Lazily initialize competency states for a session."""
        if session_id not in cls._sessions:
            cls._sessions[session_id] = {
                key: LiveCompetencyState(
                    competency_key=key,
                    display_name=COMPETENCY_DISPLAY_NAMES.get(key, key.replace("_", " ").title()),
                )
                for key in COMPETENCY_KEYWORDS
            }
        return cls._sessions[session_id]

    @classmethod
    def update_from_transcript(
        cls,
        session_id: str,
        transcript_text: str,
        question_id: str | None = None,
    ) -> None:
        """
        Scan a transcript chunk for competency keywords and update state.

        Called after each completed transcript chunk — NOT every frame.
        Pure string matching, O(keywords × text_length), <1ms typical.
        """
        if not transcript_text or not transcript_text.strip():
            return

        states = cls._ensure_session(session_id)
        text_lower = transcript_text.lower()

        for competency_key, keyword_groups in COMPETENCY_KEYWORDS.items():
            state = states[competency_key]
            for observation_label, keywords in keyword_groups.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        state.add_observation(observation_label, question_id)
                        break  # One hit per group per chunk is enough

    @classmethod
    def link_question(
        cls,
        session_id: str,
        question_id: str,
        transcript_text: str,
    ) -> None:
        """
        Link a generated question ID to competencies that were detected
        in the transcript chunk that triggered the question.

        Called from _generate_and_broadcast_questions after a question is saved.
        """
        if not transcript_text or not question_id:
            return

        states = cls._ensure_session(session_id)
        text_lower = transcript_text.lower()

        for competency_key, keyword_groups in COMPETENCY_KEYWORDS.items():
            state = states[competency_key]
            for _label, keywords in keyword_groups.items():
                for keyword in keywords:
                    if keyword in text_lower:
                        if question_id not in state.question_ids:
                            state.question_ids.append(question_id)
                        break

    @classmethod
    def get_snapshot(cls, session_id: str) -> dict:
        """
        Return the current competency state as a serializable dict,
        ready for WebSocket broadcast.
        """
        states = cls._ensure_session(session_id)

        # Only include competencies that have at least one observation
        active_competencies = [
            state.to_dict()
            for state in states.values()
            if state.evidence_count > 0
        ]

        # Also include "Collecting" competencies (with 0 evidence) for full picture
        collecting_competencies = [
            state.to_dict()
            for state in states.values()
            if state.evidence_count == 0
        ]

        # Sort: active first (by evidence count desc), then collecting
        all_competencies = sorted(
            active_competencies,
            key=lambda c: c["evidence_count"],
            reverse=True,
        ) + collecting_competencies

        # Build latest evidence grouped by competency
        latest_evidence = [
            {
                "competency": state.display_name,
                "observations": list(state.latest_observations),
            }
            for state in states.values()
            if state.latest_observations
        ]

        return {
            "competencies": all_competencies,
            "latest_evidence": latest_evidence,
        }

    @classmethod
    def clear(cls, session_id: str) -> None:
        """Remove all state for a session. Called during teardown."""
        cls._sessions.pop(session_id, None)
        logger.debug(f"[live_competency] Cleared state for session {session_id}")
