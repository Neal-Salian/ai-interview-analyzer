"""
Evidence types — structured dataclasses for the Enterprise Competency Framework.

Every piece of evidence produced by the preprocessing pipeline is represented
as a typed, immutable dataclass with a unique evidence ID.  Plugins reference
evidence by ID rather than duplicating transcript snippets, which keeps the
session_summary JSONB compact and allows cross-plugin evidence reuse.

Hierarchy:
    EvidenceItem (base)
    ├── BehaviourEvidence    — observed interview behaviours
    ├── STARExtraction       — Situation/Task/Action/Result segments
    ├── CommunicationEvidence — communication quality observations
    └── TechnicalEvidence    — technical competency observations

All types are frozen (immutable) so plugins cannot accidentally mutate them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


# ── Evidence ID generator ─────────────────────────────────────────────────────

def _make_evidence_id() -> str:
    """Generate a short, unique evidence ID (e.g. 'ev-a3b1c2d4')."""
    return f"ev-{uuid.uuid4().hex[:8]}"


# ── Base evidence item ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class EvidenceItem:
    """
    Base evidence item.  Every evidence object carries:
      - id:                   unique evidence ID for cross-referencing
      - evidence_type:        category (e.g. "leadership", "communication")
      - evidence_text:        human-readable description of what was observed
      - transcript_reference: exact transcript excerpt supporting the evidence
      - reasoning:            why this observation indicates the behaviour
      - confidence:           0.0–1.0 reliability of this evidence item
      - source:               origin (e.g. "evidence_service", "attention_tracking")
    """
    id: str = field(default_factory=_make_evidence_id)
    evidence_type: str = ""
    evidence_text: str = ""
    transcript_reference: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    source: str = "evidence_service"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "evidence_type": self.evidence_type,
            "evidence_text": self.evidence_text,
            "transcript_reference": self.transcript_reference,
            "reasoning": self.reasoning,
            "confidence": round(self.confidence, 3),
            "source": self.source,
        }


# ── Behaviour evidence ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BehaviourEvidence(EvidenceItem):
    """
    Observable interview behaviour (e.g. ownership, initiative, collaboration).

    Extracted by the evidence service from the transcript.
    Plugins score these — they never re-extract from raw text.
    """
    behaviour_type: str = ""          # e.g. "ownership", "initiative"
    star_section: str | None = None   # which STAR component this maps to

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["behaviour_type"] = self.behaviour_type
        base["star_section"] = self.star_section
        return base


# ── STAR extraction ───────────────────────────────────────────────────────────

@dataclass(frozen=True)
class STARExtraction:
    """
    A single STAR (Situation, Task, Action, Result) example extracted
    from the candidate's transcript.

    Fields:
        id:              unique evidence ID
        situation:       the context / background described
        task:            the objective or challenge
        action:          what the candidate did
        result:          the outcome achieved
        quality:         overall quality assessment (0.0–1.0)
        completeness:    fraction of STAR components present (0.0–1.0)
        missing_sections: which STAR components are absent
        transcript_reference: the raw transcript segment
        confidence:      reliability of the extraction
    """
    id: str = field(default_factory=_make_evidence_id)
    situation: str = ""
    task: str = ""
    action: str = ""
    result: str = ""
    quality: float = 0.0
    completeness: float = 0.0
    missing_sections: list[str] = field(default_factory=list)
    transcript_reference: str = ""
    confidence: float = 0.0
    source: str = "evidence_service"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "situation": self.situation,
            "task": self.task,
            "action": self.action,
            "result": self.result,
            "quality": round(self.quality, 3),
            "completeness": round(self.completeness, 3),
            "missing_sections": list(self.missing_sections),
            "transcript_reference": self.transcript_reference,
            "confidence": round(self.confidence, 3),
            "source": self.source,
        }


# ── Communication evidence ────────────────────────────────────────────────────

@dataclass(frozen=True)
class CommunicationEvidence(EvidenceItem):
    """
    Communication quality observation.

    Sub-dimensions: clarity, articulation, structure, persuasion,
    listening, speaking_confidence.
    """
    dimension: str = ""       # e.g. "clarity", "articulation"
    assessment: str = ""      # brief finding (not a numeric score)
    indicators: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["dimension"] = self.dimension
        base["assessment"] = self.assessment
        base["indicators"] = list(self.indicators)
        return base


# ── Technical evidence ────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TechnicalEvidence(EvidenceItem):
    """
    Technical competency observation.

    Links to specific skills from the job description when available.
    """
    skill: str = ""                    # e.g. "Python", "System Design"
    depth: str = ""                    # "surface", "working", "deep"
    correct_concepts: list[str] = field(default_factory=list)
    missing_concepts: list[str] = field(default_factory=list)
    inaccuracies: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        base = super().to_dict()
        base["skill"] = self.skill
        base["depth"] = self.depth
        base["correct_concepts"] = list(self.correct_concepts)
        base["missing_concepts"] = list(self.missing_concepts)
        base["inaccuracies"] = list(self.inaccuracies)
        return base


# ── Evidence collection ───────────────────────────────────────────────────────

@dataclass
class EvidenceCollection:
    """
    Container holding all evidence produced by the preprocessing pipeline.
    Attached to the enriched SessionContext for plugin consumption.

    Provides lookup-by-ID and filtered retrieval by type.
    """
    behaviours: list[BehaviourEvidence] = field(default_factory=list)
    star_extractions: list[STARExtraction] = field(default_factory=list)
    communication: list[CommunicationEvidence] = field(default_factory=list)
    technical: list[TechnicalEvidence] = field(default_factory=list)

    # ── Index for O(1) lookup by evidence ID ──────────────────────────────
    _index: dict[str, EvidenceItem | STARExtraction] = field(
        default_factory=dict, repr=False
    )

    def build_index(self) -> None:
        """Rebuild the evidence ID index after populating collections."""
        self._index.clear()
        for item in self.behaviours:
            self._index[item.id] = item
        for item in self.star_extractions:
            self._index[item.id] = item
        for item in self.communication:
            self._index[item.id] = item
        for item in self.technical:
            self._index[item.id] = item

    def get_by_id(self, evidence_id: str) -> EvidenceItem | STARExtraction | None:
        """Look up any evidence item by its unique ID."""
        return self._index.get(evidence_id)

    def get_behaviours_by_type(self, behaviour_type: str) -> list[BehaviourEvidence]:
        """Filter behaviour evidence by type (e.g. 'leadership')."""
        return [
            b for b in self.behaviours
            if b.behaviour_type.lower() == behaviour_type.lower()
        ]

    def get_communication_by_dimension(
        self, dimension: str
    ) -> list[CommunicationEvidence]:
        """Filter communication evidence by dimension (e.g. 'clarity')."""
        return [
            c for c in self.communication
            if c.dimension.lower() == dimension.lower()
        ]

    def get_technical_by_skill(self, skill: str) -> list[TechnicalEvidence]:
        """Filter technical evidence by skill name."""
        return [
            t for t in self.technical
            if t.skill.lower() == skill.lower()
        ]

    @property
    def all_evidence_ids(self) -> list[str]:
        """Return all evidence IDs in the collection."""
        return list(self._index.keys())

    def is_empty(self) -> bool:
        """True if no evidence has been extracted."""
        return (
            not self.behaviours
            and not self.star_extractions
            and not self.communication
            and not self.technical
        )

    def to_dict(self) -> dict:
        return {
            "behaviours": [b.to_dict() for b in self.behaviours],
            "star_extractions": [s.to_dict() for s in self.star_extractions],
            "communication": [c.to_dict() for c in self.communication],
            "technical": [t.to_dict() for t in self.technical],
            "total_evidence_items": len(self._index),
        }
