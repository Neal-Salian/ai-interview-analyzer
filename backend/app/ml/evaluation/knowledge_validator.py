import logging
import json
import httpx
from typing import Dict, Any

logger = logging.getLogger(__name__)

from app.core.config import settings
async def validate_knowledge(transcript: str, domain: str, rubric: Dict[str, Any]) -> Dict[str, Any]:
    """
    Uses LLM to validate the facts in the answer against the specific domain.
    Returns correct concepts, missing concepts, potential inaccuracies, and confidence.
    """
    if not transcript.strip():
        return {
            "correct_concepts": [],
            "missing_concepts": [],
            "potential_inaccuracies": [],
            "confidence_level": "Low",
        }

    prompt = f"""You are an expert evaluator in the {domain} domain.
Your task is to validate the knowledge presented in the following candidate transcript.
Focus on factual accuracy, conceptual correctness, and identifying what is missing or wrong based on standard {domain} practices.

Required Skills/Focus Areas: {', '.join(rubric.get('required_skills', []))}

Transcript:
"{transcript}"

Analyze the transcript and respond ONLY with a JSON object. No markdown formatting, no backticks, no explanation. Just raw JSON matching this structure:
{{
  "correct_concepts": ["concept 1", "concept 2"],
  "missing_concepts": ["concept 3"],
  "potential_inaccuracies": ["issue 1 description"],
  "confidence_level": "High" // Can be High, Medium, Low
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
                        "temperature": 0.1,
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
                "correct_concepts": result.get("correct_concepts", []),
                "missing_concepts": result.get("missing_concepts", []),
                "potential_inaccuracies": result.get("potential_inaccuracies", []),
                "confidence_level": result.get("confidence_level", "Medium"),
            }
            
    except Exception as e:
        logger.exception(f"[knowledge_validator] LLM request failed: {e}")
        return {
            "correct_concepts": [],
            "missing_concepts": [],
            "potential_inaccuracies": [],
            "confidence_level": "Low",
        }
