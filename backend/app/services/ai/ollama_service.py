import httpx

async def check_health() -> bool:
    """Check if Ollama is reachable."""
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get("http://localhost:11434/api/tags")
            return resp.status_code == 200
    except Exception:
        return False
