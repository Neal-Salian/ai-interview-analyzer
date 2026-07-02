import asyncio

def _do_import():
    try:
        import whisper
        return True
    except Exception:
        return False

async def check_health() -> bool:
    """Check if Whisper dependencies are available."""
    return await asyncio.to_thread(_do_import)
