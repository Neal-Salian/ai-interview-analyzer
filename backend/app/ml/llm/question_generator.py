import json
import httpx
import logging
from app.db.crud import get_job

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3.1:8b"   # swap to "llama3.1:70b" if you have the RAM

# ── Job context helper ────────────────────────────────────────────────────────

def extract_job_context(job_id: str) -> str:
    if not job_id:
        return ""
    job = get_job(job_id)
    if not job:
        return ""
    return f"Role: {job.title}\nSeniority: {job.seniority_level}\nDescription: {job.raw_description[:1000]}"


# ── Main function ─────────────────────────────────────────────────────────────

async def generate_analysis(transcript: str, job_id: str = "") -> dict:
    """
    Sends transcript chunk to local Ollama model.
    Returns structured JSON matching the existing schema.
    Drop-in replacement for the Claude version.
    
    TODO: swap OLLAMA_URL + model for Claude/Groq when deploying.
    """
    job_context = extract_job_context(job_id)

    prompt = f"""You are assisting a recruiter conducting a job interview.

{f"Job Context:{chr(10)}{job_context}{chr(10)}" if job_context else ""}
The candidate just said:
"{transcript}"

Return ONLY a valid JSON object with this exact structure. No explanation, no markdown, no backticks:
{{
    "fact_check": {{
        "has_issue": true or false,
        "correction": "one sentence correction or null"
    }},
    "pressure_question": "one tough follow-up question string",
    "lifeline_question": "one supportive follow-up question string",
    "star_feedback": "which STAR component is missing or null if complete",
    "confidence_score": a number from 1 to 10
}}"""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                OLLAMA_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,   # low temp = more consistent JSON
                        "num_predict": 400,
                    }
                }
            )
            response.raise_for_status()
            raw = response.json().get("response", "")

    except httpx.TimeoutException:
        logger.warning("[ollama] request timed out — skipping analysis for this chunk")
        return {}
    except Exception as e:
        logger.error(f"[ollama] request failed: {e}")
        return {}

    # Strip markdown fences if model wraps output anyway
    clean = raw.strip()
    if clean.startswith("```"):
        clean = clean.split("```")[1]
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        logger.warning(f"[ollama] JSON parse failed. Raw output: {raw[:200]}")
        return {}