import json
import httpx
import logging
from app.db.crud import get_job

logger = logging.getLogger(__name__)

from app.core.config import settings


def extract_job_context(job_id: str) -> str:
    if not job_id:
        return ""
    job = get_job(job_id)
    if not job:
        return ""
    return f"Role: {job.title}\nSeniority: {job.seniority_level}\nDescription: {job.raw_description[:1000]}"


async def generate_analysis(transcript: str, job_id: str = "") -> dict:
    job_context = extract_job_context(job_id)

    prompt = f"""You are assisting a recruiter conducting a job interview.

{f"Job Context:{chr(10)}{job_context}{chr(10)}" if job_context else ""}The candidate just said:
"{transcript}"

Respond with ONLY a JSON object. No explanation. No markdown. No backticks. Just raw JSON:
{{"fact_check": {{"has_issue": false, "correction": null}}, "pressure_question": "your question here", "lifeline_question": "your question here", "star_feedback": null, "confidence_score": 7}}"""

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
                        "num_predict": 300,
                    }
                }
            )
            response.raise_for_status()

    except httpx.TimeoutException:
        logger.warning("[ollama] request timed out")
        return {}
    except httpx.ConnectError:
        logger.exception("[ollama] cannot connect — is Ollama running on port 11434?")
        return {}
    except Exception as e:
        logger.exception(f"[ollama] request failed: {e}")
        return {}

    # --- Parse the outer Ollama envelope ---
    try:
        envelope = response.json()
    except json.JSONDecodeError as e:
        logger.warning(f"[ollama] outer envelope is not valid JSON: {e}")
        logger.warning(f"[ollama] raw response text: {response.text[:300]}")
        return {}

    raw = envelope.get("response", "")
    if not raw:
        logger.warning(f"[ollama] empty response field. Full envelope: {envelope}")
        return {}

    # --- Strip markdown fences if model ignored instructions ---
    clean = raw.strip()
    if "```" in clean:
        # extract content between first ``` and last ```
        parts = clean.split("```")
        # parts[1] is between first pair of backticks
        clean = parts[1] if len(parts) >= 2 else clean
        if clean.startswith("json"):
            clean = clean[4:]
    clean = clean.strip()

    # --- Find the JSON object even if model adds preamble text ---
    start = clean.find("{")
    end = clean.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning(f"[ollama] no JSON object found in response: {clean[:200]}")
        return {}
    clean = clean[start:end]

    # --- Parse the actual result ---
    try:
        return json.loads(clean)
    except json.JSONDecodeError as e:
        logger.warning(f"[ollama] JSON parse failed: {e}")
        logger.warning(f"[ollama] attempted to parse: {clean[:300]}")
        return {}