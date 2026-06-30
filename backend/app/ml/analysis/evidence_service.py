"""
Evidence Service — single-pass LLM evidence extraction.

This is the ONLY place in the entire Enterprise Competency Framework where
the LLM is invoked.  It executes exactly ONCE per session teardown and
produces structured evidence objects that all plugins consume.

Responsibilities:
  - STAR extraction
  - Behaviour evidence extraction
  - Communication analysis
  - Technical evidence extraction

The service is provider-agnostic: it calls an internal _call_llm() function
that currently uses Ollama but can be swapped to Claude / OpenAI / Gemini
without touching any plugin code.

No plugin should ever call the LLM directly.  Plugins only consume evidence.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.ml.analysis.evidence_types import (
    BehaviourEvidence,
    CommunicationEvidence,
    EvidenceCollection,
    STARExtraction,
    TechnicalEvidence,
)

logger = logging.getLogger(__name__)

# ── Evidence pipeline version ─────────────────────────────────────────────────
# Plugins declare `requires = {"star": 1, "behaviour_evidence": 1}` etc.
# Bump this when the extraction schema changes.

EVIDENCE_PIPELINE_VERSIONS = {
    "star": 1,
    "behaviour_evidence": 1,
    "communication_evidence": 1,
    "technical_evidence": 1,
}


# ── LLM provider abstraction ─────────────────────────────────────────────────

def _call_llm(prompt: str, max_tokens: int = 2000) -> str:
    """
    Call the LLM provider and return the raw response text.

    Currently uses Ollama (matching the existing project pattern).
    Designed to be swapped to any provider without affecting callers.
    This function is SYNCHRONOUS — it's called via asyncio.to_thread()
    from the teardown pipeline.
    """
    import httpx
    from app.core.config import settings

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": max_tokens,
                    },
                },
            )
            response.raise_for_status()
            envelope = response.json()
            return envelope.get("response", "")

    except Exception as e:
        logger.warning(f"[evidence_service] LLM call failed: {e}")
        return ""


def _parse_json_response(raw: str) -> dict:
    """Parse JSON from LLM response, handling markdown fences and preamble."""
    clean = raw.strip()

    # Strip markdown fences
    if "```" in clean:
        parts = clean.split("```")
        clean = parts[1] if len(parts) >= 2 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    # Find JSON object
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        return {}

    try:
        return json.loads(clean[start:end])
    except json.JSONDecodeError as e:
        logger.warning(f"[evidence_service] JSON parse failed: {e}")
        return {}


# ── Main extraction function ──────────────────────────────────────────────────


def extract_evidence(
    transcript: str,
    job_title: str = "",
    job_skills: list[str] | None = None,
    candidate_name: str = "",
) -> EvidenceCollection:
    """
    Execute the single-pass evidence extraction pipeline.

    This function is called ONCE per session teardown.  It sends ONE
    structured prompt to the LLM and parses the response into typed
    evidence objects.

    Args:
        transcript:     full cleaned transcript text
        job_title:      role being interviewed for
        job_skills:     skills from the job description
        candidate_name: candidate's name for context

    Returns:
        EvidenceCollection containing all extracted evidence.
        Returns an empty collection if the LLM call fails (graceful fallback).
    """
    if not transcript or not transcript.strip():
        logger.info("[evidence_service] Empty transcript — returning empty evidence")
        return EvidenceCollection()

    skills_str = ", ".join(job_skills or [])
    word_count = len(transcript.split())

    prompt = _build_extraction_prompt(
        transcript=transcript,
        job_title=job_title,
        skills_str=skills_str,
        candidate_name=candidate_name,
        word_count=word_count,
    )

    raw_response = _call_llm(prompt, max_tokens=3000)
    if not raw_response:
        logger.warning("[evidence_service] Empty LLM response — returning empty evidence")
        return EvidenceCollection()

    parsed = _parse_json_response(raw_response)
    if not parsed:
        logger.warning("[evidence_service] Failed to parse LLM response — returning empty evidence")
        return EvidenceCollection()

    return _build_evidence_collection(parsed)


# ── Prompt construction ───────────────────────────────────────────────────────


def _build_extraction_prompt(
    transcript: str,
    job_title: str,
    skills_str: str,
    candidate_name: str,
    word_count: int,
) -> str:
    """
    Build the single structured extraction prompt.

    This prompt extracts ALL evidence types in one LLM call:
    STAR examples, behavioural evidence, communication observations,
    and technical competency evidence.
    """
    # Truncate very long transcripts to stay within context window
    max_chars = 8000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[... transcript truncated ...]"

    return f"""You are an expert interview analyst. Analyze the following interview transcript and extract structured evidence.

CONTEXT:
- Candidate: {candidate_name or "Unknown"}
- Role: {job_title or "Not specified"}
- Required Skills: {skills_str or "Not specified"}
- Transcript Length: {word_count} words

TRANSCRIPT:
\"\"\"{transcript}\"\"\"

Extract the following and respond with ONLY a JSON object. No markdown, no backticks, no explanation.

{{
  "star_examples": [
    {{
      "situation": "brief description of the context",
      "task": "the objective or challenge",
      "action": "what the candidate did",
      "result": "the outcome achieved",
      "quality": 0.8,
      "transcript_excerpt": "exact quote from transcript"
    }}
  ],
  "behaviours": [
    {{
      "type": "ownership|initiative|collaboration|leadership|learning_agility|adaptability|communication|decision_making|problem_solving|customer_focus|accountability|resilience|conflict_resolution|time_management",
      "evidence": "what was observed",
      "reasoning": "why this indicates the behaviour",
      "transcript_excerpt": "exact quote from transcript",
      "confidence": 0.8,
      "star_section": "situation|task|action|result|null"
    }}
  ],
  "communication": [
    {{
      "dimension": "clarity|articulation|structure|persuasion|listening|speaking_confidence",
      "assessment": "brief finding",
      "indicators": ["specific indicator 1", "specific indicator 2"],
      "transcript_excerpt": "exact quote from transcript",
      "confidence": 0.8
    }}
  ],
  "technical": [
    {{
      "skill": "specific skill name",
      "depth": "surface|working|deep",
      "correct_concepts": ["concept 1"],
      "missing_concepts": ["concept 1"],
      "inaccuracies": [],
      "transcript_excerpt": "exact quote from transcript",
      "confidence": 0.8
    }}
  ],
  "overall_confidence": 0.7
}}

RULES:
- Only extract evidence that is directly observable in the transcript.
- Never fabricate quotes or behaviours.
- If a section has no evidence, return an empty array.
- Confidence values must reflect how clearly the evidence supports the finding.
- transcript_excerpt must be actual text from the transcript, not paraphrased.
- Each STAR example must have at least 2 of the 4 components to be included.
- Behaviour types should match the predefined list above.
- Be thorough but precise — quality over quantity."""


# ── Evidence collection builder ───────────────────────────────────────────────


def _build_evidence_collection(parsed: dict) -> EvidenceCollection:
    """Convert the parsed LLM JSON response into typed evidence objects."""
    collection = EvidenceCollection()

    overall_confidence = parsed.get("overall_confidence", 0.5)

    # ── STAR extractions ──────────────────────────────────────────────────
    for star in parsed.get("star_examples", []):
        situation = star.get("situation", "")
        task = star.get("task", "")
        action = star.get("action", "")
        result = star.get("result", "")

        # Compute completeness
        present = sum(1 for s in [situation, task, action, result] if s.strip())
        missing = []
        if not situation.strip():
            missing.append("situation")
        if not task.strip():
            missing.append("task")
        if not action.strip():
            missing.append("action")
        if not result.strip():
            missing.append("result")

        if present >= 2:  # only include if at least 2 components
            collection.star_extractions.append(STARExtraction(
                situation=situation,
                task=task,
                action=action,
                result=result,
                quality=star.get("quality", 0.5),
                completeness=present / 4,
                missing_sections=missing,
                transcript_reference=star.get("transcript_excerpt", ""),
                confidence=star.get("quality", overall_confidence),
            ))

    # ── Behaviour evidence ────────────────────────────────────────────────
    for beh in parsed.get("behaviours", []):
        btype = beh.get("type", "")
        if not btype:
            continue
        collection.behaviours.append(BehaviourEvidence(
            evidence_type=btype,
            behaviour_type=btype,
            evidence_text=beh.get("evidence", ""),
            transcript_reference=beh.get("transcript_excerpt", ""),
            reasoning=beh.get("reasoning", ""),
            confidence=beh.get("confidence", overall_confidence),
            star_section=beh.get("star_section"),
            source="evidence_service",
        ))

    # ── Communication evidence ────────────────────────────────────────────
    for comm in parsed.get("communication", []):
        dimension = comm.get("dimension", "")
        if not dimension:
            continue
        collection.communication.append(CommunicationEvidence(
            evidence_type="communication",
            dimension=dimension,
            assessment=comm.get("assessment", ""),
            indicators=comm.get("indicators", []),
            evidence_text=comm.get("assessment", ""),
            transcript_reference=comm.get("transcript_excerpt", ""),
            confidence=comm.get("confidence", overall_confidence),
            source="evidence_service",
        ))

    # ── Technical evidence ────────────────────────────────────────────────
    for tech in parsed.get("technical", []):
        skill = tech.get("skill", "")
        if not skill:
            continue
        collection.technical.append(TechnicalEvidence(
            evidence_type="technical",
            skill=skill,
            depth=tech.get("depth", "surface"),
            correct_concepts=tech.get("correct_concepts", []),
            missing_concepts=tech.get("missing_concepts", []),
            inaccuracies=tech.get("inaccuracies", []),
            evidence_text=f"{skill}: {tech.get('depth', 'surface')} knowledge",
            transcript_reference=tech.get("transcript_excerpt", ""),
            confidence=tech.get("confidence", overall_confidence),
            source="evidence_service",
        ))

    # Build the ID index for O(1) lookups
    collection.build_index()

    logger.info(
        f"[evidence_service] Extraction complete: "
        f"{len(collection.star_extractions)} STAR, "
        f"{len(collection.behaviours)} behaviours, "
        f"{len(collection.communication)} communication, "
        f"{len(collection.technical)} technical"
    )

    return collection
