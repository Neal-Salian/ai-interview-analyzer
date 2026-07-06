"""
RTMP Service — owns RTMP consumer lifecycle.

Responsibilities:
  - Health-check the nginx-rtmp stats endpoint
  - Start the RTMP consumer for a session
  - Verify successful startup
  - Return startup success/failure with error context
  - Track running consumer tasks for future teardown
"""

import time
import asyncio
import logging
from typing import Dict, Any, Optional

import httpx

from app.core.logging_config import log_event

logger = logging.getLogger(__name__)

# No local _consumer_tasks dict. We use app.core.registry instead.

# How long to wait for the RTMP stream to open before declaring failure
STARTUP_TIMEOUT_SECONDS = 15


async def check_health() -> bool:
    """Check if the RTMP server is reachable."""
    try:
        from app.core.config import settings
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(settings.RTMP_STAT_URL)
            return resp.status_code == 200
    except Exception:
        return False


async def start(
    session_id: str,
    rtmp_url: str,
    recruiter_id: str = "",
    job_id: str = "",
) -> Dict[str, Any]:
    """
    Start the RTMP consumer for a session.

    Returns a result dict:
        {
            "success": bool,
            "startup_duration_ms": int,
            "error": str | None,     # human-readable failure reason
            "error_type": str | None  # exception class name
        }

    The consumer is launched as an asyncio task and monitored for
    STARTUP_TIMEOUT_SECONDS to confirm it opened the stream successfully.
    """
    start_time = time.time()

    log_event(logger, "rtmp_start_requested",
              session_id=session_id, recruiter_id=recruiter_id,
              rtmp_url=rtmp_url)

    # ── 1. Pre-flight: verify RTMP server is reachable ──────────────────
    if not await check_health():
        duration_ms = int((time.time() - start_time) * 1000)
        reason = "RTMP server unreachable (nginx-rtmp stats endpoint down)."
        log_event(logger, "rtmp_failed", level=logging.ERROR,
                  session_id=session_id, recruiter_id=recruiter_id,
                  failure_reason=reason, startup_duration_ms=duration_ms)
        return {
            "success": False,
            "startup_duration_ms": duration_ms,
            "error": reason,
            "error_type": "RTMPServerUnreachable",
        }

    # ── 2. Launch consumer in background task ───────────────────────────
    # Import here to keep PyAV out of the service module's top-level scope.
    from app.ml.stream.rtmp_consumer import consume_stream
    from app.core.registry import register_session, cancel_session

    # Signal used to detect whether the consumer opened the stream.
    startup_event = asyncio.Event()
    startup_error: Dict[str, Any] = {}

    async def _monitored_consumer():
        """Thin wrapper around consume_stream that signals startup status."""
        try:
            # Import av here so we can attempt to open and signal quickly
            import av
            container = await asyncio.to_thread(
                av.open, rtmp_url, timeout=5.0
            )
            # If we reach here, the stream opened successfully
            startup_event.set()

            # Now run the actual packet processing loop
            # We re-use the opened container by monkey-patching into the
            # existing consumer flow.  However, the existing consume_stream
            # opens its own container, so instead we close this probe
            # container and let consume_stream re-open.  This is the safest
            # approach to avoid changing the consumer internals.
            await asyncio.to_thread(container.close)

            # Run the real consumer with retry
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"[consumer] attempt {attempt}/{max_retries} for session {session_id}")
                    await consume_stream(session_id, rtmp_url, job_id)
                    logger.info(f"[consumer] stream ended cleanly for session {session_id}")
                    break
                except asyncio.CancelledError:
                    logger.info(f"[consumer] cancelled for session {session_id}")
                    raise
                except Exception as e:
                    logger.warning(f"[consumer] attempt {attempt} failed: {e}")
                    if attempt < max_retries:
                        logger.info("[consumer] retrying in 3 seconds...")
                        await asyncio.sleep(3)
                    else:
                        logger.error(f"[consumer] all {max_retries} attempts exhausted for session {session_id}")

        except asyncio.CancelledError:
            raise
        except Exception as e:
            startup_error["error"] = str(e)
            startup_error["error_type"] = type(e).__name__
            startup_event.set()  # unblock the waiter

    task = asyncio.create_task(_monitored_consumer())
    register_session(session_id, task)

    # ── 3. Wait for startup signal or timeout ───────────────────────────
    try:
        await asyncio.wait_for(startup_event.wait(), timeout=STARTUP_TIMEOUT_SECONDS)
    except asyncio.TimeoutError:
        duration_ms = int((time.time() - start_time) * 1000)
        reason = f"RTMP consumer startup timed out after {STARTUP_TIMEOUT_SECONDS}s."
        log_event(logger, "rtmp_failed", level=logging.ERROR,
                  session_id=session_id, recruiter_id=recruiter_id,
                  failure_reason=reason, startup_duration_ms=duration_ms)
        # Cancel the hung task
        await cancel_session(session_id)
        return {
            "success": False,
            "startup_duration_ms": duration_ms,
            "error": reason,
            "error_type": "StartupTimeout",
        }

    duration_ms = int((time.time() - start_time) * 1000)

    # ── 4. Evaluate startup result ──────────────────────────────────────
    if startup_error:
        reason = startup_error.get("error", "Unknown consumer startup error.")
        error_type = startup_error.get("error_type", "Unknown")
        log_event(logger, "rtmp_failed", level=logging.ERROR,
                  session_id=session_id, recruiter_id=recruiter_id,
                  failure_reason=reason, error_type=error_type,
                  startup_duration_ms=duration_ms)
        await cancel_session(session_id)
        return {
            "success": False,
            "startup_duration_ms": duration_ms,
            "error": reason,
            "error_type": error_type,
        }

    # ── 5. Success ──────────────────────────────────────────────────────
    log_event(logger, "rtmp_started",
              session_id=session_id, recruiter_id=recruiter_id,
              startup_duration_ms=duration_ms)
    return {
        "success": True,
        "startup_duration_ms": duration_ms,
        "error": None,
        "error_type": None,
    }


# These functions are no longer needed, use app.core.registry instead.
def get_consumer_task(session_id: str) -> Optional[asyncio.Task]:
    """Deprecated: Use app.core.registry instead."""
    from app.core.registry import get_bundle
    bundle = get_bundle(session_id)
    return bundle.consumer_task if bundle else None


def remove_consumer_task(session_id: str) -> Optional[asyncio.Task]:
    """Deprecated: Use app.core.registry.cancel_session instead."""
    pass
