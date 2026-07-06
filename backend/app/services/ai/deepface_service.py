import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import deepface
    _deepface_available = True
except Exception as e:
    logger.warning(f"DeepFace not available: {e}")
    _deepface_available = False

async def check_health() -> bool:
    """Check if DeepFace dependencies are available."""
    # We return the pre-evaluated availability to avoid importing in a worker thread,
    # which causes global import lock deadlocks.
    return _deepface_available
