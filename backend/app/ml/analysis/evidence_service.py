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
import time
import asyncio
from datetime import datetime
from typing import Any

from app.ml.analysis.evidence_types import (
    BehaviourEvidence,
    CommunicationEvidence,
    EvidenceCollection,
    STARExtraction,
    TechnicalEvidence,
)
from app.ml.analysis.interfaces import SessionContext

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

def _call_llm(prompt: str, max_tokens: int = 3000) -> str:
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


async def build_evidence(ctx: SessionContext) -> EvidenceCollection:
    """
    Execute the single-pass evidence extraction pipeline.

    This function is called ONCE per session teardown. It sends ONE
    structured prompt to the LLM and parses the response into typed
    evidence objects.
    
    If it fails, it retries exactly once with a simplified prompt.
    If it fails again, it returns an empty EvidenceCollection to fallback gracefully.
    """
    start_time = time.time()
    logger.info("[evidence_service] Evidence extraction started")

    if not ctx.candidate_segments:
        logger.info("[evidence_service] Empty candidate transcript — returning empty evidence")
        return EvidenceCollection()

    # Build numbered transcript
    numbered_transcript = []
    for i, seg in enumerate(ctx.candidate_segments):
        text = seg.get("text", "").strip()
        numbered_transcript.append(f"[Chunk Index: {i}] {text}")
    
    transcript_text = "\n".join(numbered_transcript)
    skills_str = ", ".join(ctx.job_skills or [])
    word_count = len(transcript_text.split())

    prompt = _build_extraction_prompt(
        transcript=transcript_text,
        job_title=ctx.job_title,
        skills_str=skills_str,
        candidate_name=ctx.candidate_name,
        word_count=word_count,
    )

    retry_used = False
    fallback_used = False
    
    try:
        raw_response = await asyncio.to_thread(_call_llm, prompt, 3000)
        if not raw_response:
            raise ValueError("Empty LLM response")
            
        parsed = _parse_json_response(raw_response)
        if not parsed:
            raise ValueError("Malformed JSON")
            
    except Exception as e:
        logger.warning(f"[evidence_service] LLM call failed: {e}. Attempting retry with simplified prompt.")
        retry_used = True
        
        simplified_prompt = _build_simplified_prompt(
            transcript=transcript_text,
            job_title=ctx.job_title,
            skills_str=skills_str,
            candidate_name=ctx.candidate_name,
            word_count=word_count,
        )
        try:
            raw_response = await asyncio.to_thread(_call_llm, simplified_prompt, 3000)
            if not raw_response:
                raise ValueError("Empty LLM response on retry")
                
            parsed = _parse_json_response(raw_response)
            if not parsed:
                raise ValueError("Malformed JSON on retry")
        except Exception as retry_e:
            logger.warning(f"[evidence_service] Retry failed: {retry_e}. Using fallback (empty evidence).")
            fallback_used = True
            parsed = {}
            
    collection = _build_evidence_collection(parsed, ctx.candidate_segments)
    
    processing_ms = int((time.time() - start_time) * 1000)
    
    collection.metadata = {
        "model": "ollama", # Hardcoded abstraction alias for now
        "prompt_version": 2,
        "processing_started": datetime.fromtimestamp(start_time).isoformat(),
        "processing_finished": datetime.now().isoformat(),
        "processing_ms": processing_ms,
        "retry_used": retry_used,
        "fallback_used": fallback_used,
        "candidate_word_count": word_count,
        "chunk_count": len(ctx.candidate_segments),
        "behaviour_count": len(collection.behaviours),
        "communication_count": len(collection.communication),
        "technical_count": len(collection.technical),
        "star_count": len(collection.star_extractions),
    }

    logger.info(
        f"[evidence_service] Evidence Extraction Complete\n"
        f"Candidate Words: {word_count}\n"
        f"Chunks: {len(ctx.candidate_segments)}\n"
        f"Behaviours: {len(collection.behaviours)}\n"
        f"STAR Stories: {len(collection.star_extractions)}\n"
        f"Communication: {len(collection.communication)}\n"
        f"Technical: {len(collection.technical)}\n"
        f"Retry Used: {'Yes' if retry_used else 'No'}\n"
        f"Fallback Used: {'Yes' if fallback_used else 'No'}\n"
        f"Duration: {processing_ms / 1000:.1f} sec"
    )

    return collection


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
    max_chars = 12000
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
      "transcript_excerpt": "exact quote from transcript",
      "transcript_index": 0
    }}
  ],
  "behaviours": [
    {{
      "type": "ownership|initiative|collaboration|leadership|learning_agility|adaptability|communication|decision_making|problem_solving|customer_focus|accountability|resilience|conflict_resolution|time_management",
      "evidence": "what was observed",
      "reasoning": "why this indicates the behaviour",
      "transcript_excerpt": "exact quote from transcript",
      "transcript_index": 0,
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
      "transcript_index": 0,
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
      "transcript_index": 0,
      "confidence": 0.8
    }}
  ],
  "overall_confidence": 0.7
}}

CRITICAL RULES:
- Never infer unsupported behaviours.
- Never assign competency scores.
- Never recommend hiring.
- Never predict personality.
- Never invent evidence.
- Return nothing if evidence is insufficient (empty arrays are correct).
- Only extract evidence that is directly observable in the transcript.
- transcript_excerpt must be actual text from the transcript, not paraphrased.
- transcript_index must refer strictly to the exact [Chunk Index: X] of the transcript where the excerpt was found.
- Confidence values must reflect how clearly the evidence supports the finding."""


def _build_simplified_prompt(
    transcript: str,
    job_title: str,
    skills_str: str,
    candidate_name: str,
    word_count: int,
) -> str:
    """
    Build a simplified, highly structured prompt for retries when the LLM
    fails to return valid JSON. This strips away complex instructions to ensure
    parseable outputs.
    """
    max_chars = 12000
    if len(transcript) > max_chars:
        transcript = transcript[:max_chars] + "\n[... transcript truncated ...]"

    return f"""Analyze the transcript and output ONLY a valid JSON object matching the schema below. Do not include any text outside the JSON.

{{
  "star_examples": [],
  "behaviours": [],
  "communication": [],
  "technical": [],
  "overall_confidence": 0.5
}}

Transcript:
\"\"\"{transcript}\"\"\"

Only populate arrays if clear evidence is found. Ensure transcript_index is an integer matching the chunk index."""


# ── Evidence collection builder ───────────────────────────────────────────────


def _get_segment_info(index: int | None, segments: list[dict]) -> tuple[str | None, str | None]:
    if index is not None and isinstance(index, int) and 0 <= index < len(segments):
        return segments[index].get("id"), segments[index].get("timestamp")
    return None, None


def _build_evidence_collection(parsed: dict, segments: list[dict]) -> EvidenceCollection:
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

        transcript_index = star.get("transcript_index")
        t_id, t_ts = _get_segment_info(transcript_index, segments)

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
                transcript_index=transcript_index,
                transcript_id=t_id,
                timestamp=t_ts,
                confidence=star.get("quality", overall_confidence),
            ))

    # ── Behaviour evidence ────────────────────────────────────────────────
    for beh in parsed.get("behaviours", []):
        btype = beh.get("type", "")
        if not btype:
            continue
        
        transcript_index = beh.get("transcript_index")
        t_id, t_ts = _get_segment_info(transcript_index, segments)

        collection.behaviours.append(BehaviourEvidence(
            evidence_type=btype,
            behaviour_type=btype,
            evidence_text=beh.get("evidence", ""),
            transcript_reference=beh.get("transcript_excerpt", ""),
            transcript_index=transcript_index,
            transcript_id=t_id,
            timestamp=t_ts,
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
        
        transcript_index = comm.get("transcript_index")
        t_id, t_ts = _get_segment_info(transcript_index, segments)

        collection.communication.append(CommunicationEvidence(
            evidence_type="communication",
            dimension=dimension,
            assessment=comm.get("assessment", ""),
            indicators=comm.get("indicators", []),
            evidence_text=comm.get("assessment", ""),
            transcript_reference=comm.get("transcript_excerpt", ""),
            transcript_index=transcript_index,
            transcript_id=t_id,
            timestamp=t_ts,
            confidence=comm.get("confidence", overall_confidence),
            source="evidence_service",
        ))

    # ── Technical evidence ────────────────────────────────────────────────
    for tech in parsed.get("technical", []):
        skill = tech.get("skill", "")
        if not skill:
            continue

        transcript_index = tech.get("transcript_index")
        t_id, t_ts = _get_segment_info(transcript_index, segments)

        collection.technical.append(TechnicalEvidence(
            evidence_type="technical",
            skill=skill,
            depth=tech.get("depth", "surface"),
            correct_concepts=tech.get("correct_concepts", []),
            missing_concepts=tech.get("missing_concepts", []),
            inaccuracies=tech.get("inaccuracies", []),
            evidence_text=f"{skill}: {tech.get('depth', 'surface')} knowledge",
            transcript_reference=tech.get("transcript_excerpt", ""),
            transcript_index=transcript_index,
            transcript_id=t_id,
            timestamp=t_ts,
            confidence=tech.get("confidence", overall_confidence),
            source="evidence_service",
        ))

    # Build the ID index for O(1) lookups
    collection.build_index()

    return collection
