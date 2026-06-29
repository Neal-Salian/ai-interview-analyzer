"""
Explanation engine — calls Ollama to generate human-readable explanations.

Reuses the same Ollama integration pattern as question_generator.py:
- Same OLLAMA_URL (localhost:11434)
- Same OLLAMA_MODEL (llama3.1:8b)
- Same JSON stripping logic
- Same timeout and error handling

The key difference: prompts are constrained to pre-computed evidence
from the metric framework, preventing the LLM from hallucinating.
"""

import logging
import httpx

logger = logging.getLogger(__name__)

from app.core.config import settings


async def generate_explanation(prompt: str) -> str:
    """
    Call Ollama to generate a human-readable explanation.

    Args:
        prompt: fully constructed prompt from context_builder.py

    Returns:
        str: human-readable explanation text.
        Returns error message string on failure (never raises).
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # slightly creative for explanations
                        "num_predict": 200,  # 2-4 sentences
                    },
                },
            )
            response.raise_for_status()

    except httpx.TimeoutException:
        logger.warning("[EXPLAIN] Ollama request timed out")
        return "Explanation service timed out. Please try again."
    except httpx.ConnectError:
        logger.exception("[EXPLAIN] Cannot connect to Ollama — is it running on port 11434?")
        return "Explanation service is not available. Ensure the local AI model is running."
    except Exception as e:
        logger.exception(f"[EXPLAIN] Request failed: {e}")
        return f"Explanation service error: {str(e)}"

    # Parse the Ollama response envelope
    try:
        envelope = response.json()
    except Exception as e:
        logger.warning(f"[EXPLAIN] Invalid JSON response from Ollama: {e} | body={response.text[:200]}")
        return "Could not parse explanation response."

    raw = envelope.get("response", "").strip()

    if not raw:
        return "No explanation was generated. The model returned an empty response."

    # Clean up: remove any markdown or code fences
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(
            line for line in lines
            if not line.strip().startswith("```")
        ).strip()

    return raw
