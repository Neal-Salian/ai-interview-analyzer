"""
Candidate Attribution Service.

Separates raw transcript text into Candidate and Recruiter segments using LLM reasoning.
Returns a structured JSON conversation timeline.
"""

import json
import logging
import httpx
from typing import Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

async def perform_attribution(
    full_transcript: str, 
    candidate_name: str, 
    job_title: str,
    recent_questions: list[dict] = None
) -> Dict[str, Any]:
    """
    Calls the LLM to separate the full transcript into structured segments.
    
    Returns:
    {
      "segments": [
        {
          "speaker": "Candidate" | "Recruiter" | "Unknown",
          "text": "...",
          "confidence": 0.95,
          "reason": "..."
        }
      ]
    }
    """
    if not full_transcript or not full_transcript.strip():
        return {"segments": []}

    questions_context = ""
    if recent_questions:
        q_texts = [q.get("question_text") for q in recent_questions if q.get("question_text")]
        if q_texts:
            questions_context = "Recent questions suggested to the recruiter:\n" + "\n".join(f"- {q}" for q in q_texts)

    prompt = f"""You are an AI interview analyzer. Your task is to perform Candidate Attribution.
Separate the following raw transcript into conversational segments assigned to the Candidate or Recruiter.

CONTEXT:
Candidate Name: {candidate_name if candidate_name else 'Unknown'}
Job Title: {job_title if job_title else 'Unknown'}
{questions_context}

RAW TRANSCRIPT:
"{full_transcript}"

INSTRUCTIONS:
1. Divide the transcript into continuous blocks spoken by a single person.
2. Attribute each block to either "Candidate", "Recruiter", or "Unknown".
3. Assign a confidence score (0.0 to 1.0) and a brief reason for the attribution (e.g., "Answering technical question", "Greeting the candidate").
4. If it's unclear who is speaking, use "Unknown". Do NOT hallucinate or guess if it is highly ambiguous.
5. Do NOT change or summarize the text itself. The combined text of all segments should mostly match the original transcript.

OUTPUT FORMAT:
Respond ONLY with a JSON object matching this structure. No markdown, no backticks, no explanations.
{{
  "segments": [
    {{
      "speaker": "Recruiter",
      "text": "Tell me about yourself.",
      "confidence": 0.98,
      "reason": "Interview question"
    }},
    {{
      "speaker": "Candidate",
      "text": "I worked on...",
      "confidence": 0.95,
      "reason": "Direct response"
    }}
  ]
}}
"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,  # Low temperature for strict adherence to text
                        "num_predict": 2048,
                    }
                }
            )
            response.raise_for_status()
            
            raw = response.json().get("response", "")
            # Clean up potential markdown formatting
            clean = raw.strip()
            if "```" in clean:
                parts = clean.split("```")
                clean = parts[1] if len(parts) >= 2 else clean
                if clean.startswith("json"):
                    clean = clean[4:]
            
            start = clean.find("{")
            end = clean.rfind("}") + 1
            if start != -1 and end != 0:
                clean = clean[start:end]
            
            result = json.loads(clean)
            
            # Validate output structure
            if "segments" not in result or not isinstance(result["segments"], list):
                raise ValueError("LLM output missing 'segments' list")
                
            # Normalize speaker names
            valid_speakers = {"Candidate", "Recruiter", "Unknown"}
            for seg in result["segments"]:
                if seg.get("speaker") not in valid_speakers:
                    seg["speaker"] = "Unknown"
                
            return result
            
    except Exception as e:
        logger.exception(f"[candidate_attribution] Attribution failed: {e}")
        # Graceful degradation: return the entire transcript as Unknown
        return {
            "segments": [
                {
                    "speaker": "Unknown",
                    "text": full_transcript,
                    "confidence": 0.0,
                    "reason": "Attribution service failed. Defaulting to Unknown."
                }
            ]
        }
