import asyncio
import logging

logger = logging.getLogger(__name__)

try:
    import whisper
    _whisper_available = True
except Exception as e:
    logger.warning(f"Whisper not available: {e}")
    _whisper_available = False

async def check_health() -> bool:
    """Check if Whisper dependencies are available."""
    # We return the pre-evaluated availability to avoid importing in a worker thread,
    # which causes global import lock deadlocks.
    return _whisper_available
