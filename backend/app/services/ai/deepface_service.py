import asyncio

def _do_import():
    try:
        import deepface
        return True
    except Exception:
        return False

async def check_health() -> bool:
    """Check if DeepFace dependencies are available."""
    return await asyncio.to_thread(_do_import)
