async def check_health() -> bool:
    """Check if DeepFace dependencies are available."""
    try:
        import deepface
        return True
    except Exception:
        return False
