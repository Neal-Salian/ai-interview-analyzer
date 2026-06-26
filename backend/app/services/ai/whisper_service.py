async def check_health() -> bool:
    """Check if Whisper dependencies are available."""
    try:
        import whisper
        return True
    except Exception:
        return False
