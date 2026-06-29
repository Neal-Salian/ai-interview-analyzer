import logging
import json
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

from app.core.config import settings
async def evaluate_llm(transcript: str, domain: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluates the reasoning, communication, and overall quality using LLM.
    Returns score, strengths, improvement areas, and overall assessment.
    """
    if not transcript.strip():
        return {
            "score": 0.0,
            "strengths": [],
            "improvement_areas": ["No answer provided"],
            "overall_assessment": "The candidate did not provide a meaningful response."
        }

    prompt = f"""You are an expert interviewer evaluating a candidate for a {domain} role.
The desired tone for communication is: {rubric.get('tone', 'professional')}.

Candidate Transcript:
"{transcript}"

Evaluate the candidate's answer for communication quality, reasoning logic, and clarity.
Assign a score from 0.0 to 10.0 (where 10 is perfect).

Respond ONLY with a JSON object. No markdown, no backticks, no explanation. Just raw JSON matching this structure:
{{
  "score": 7.5,
  "strengths": ["clear communication", "logical flow"],
  "improvement_areas": ["could use more examples"],
  "overall_assessment": "Good general understanding but lacks depth."
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
                        "temperature": 0.2,
                        "num_predict": 400,
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
            return {
                "score": float(result.get("score", 5.0)),
                "strengths": result.get("strengths", []),
                "improvement_areas": result.get("improvement_areas", []),
                "overall_assessment": result.get("overall_assessment", ""),
            }
            
    except Exception as e:
        logger.exception(f"[llm_evaluator] LLM request failed: {e}")
        return {
            "score": 0.0,
            "strengths": [],
            "improvement_areas": ["Failed to evaluate answer logic"],
            "overall_assessment": "Evaluation service unavailable."
        }
