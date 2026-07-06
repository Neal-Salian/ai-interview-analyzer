import httpx

async def check_health() -> bool:
    """Check if Ollama is reachable and the required model is available."""
    from app.core.config import settings
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
            return settings.OLLAMA_MODEL in models
    except Exception:
        return False
