import asyncio
import logging
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: int
    rolling_window: deque = field(default_factory=lambda: deque(maxlen=10))
    full_transcript: str = ""
    tier2_healthy: bool = True


@dataclass
class SessionTaskBundle:
    consumer_task: asyncio.Task
    tier2_tasks: set[asyncio.Task]
    state: SessionState


# Global registry: session_id → SessionTaskBundle
_registry: dict[int, SessionTaskBundle] = {}


def register_session(
    session_id: int,
    consumer_task: asyncio.Task,
    state: SessionState,
) -> None:
    _registry[session_id] = SessionTaskBundle(
        consumer_task=consumer_task,
        tier2_tasks=set(),
        state=state,
    )
    logger.info(f"[registry] registered session {session_id}")


def get_bundle(session_id: int) -> SessionTaskBundle | None:
    return _registry.get(session_id)


def add_tier2_task(session_id: int, task: asyncio.Task) -> None:
    bundle = _registry.get(session_id)
    if bundle:
        bundle.tier2_tasks.add(task)
        task.add_done_callback(lambda t: bundle.tier2_tasks.discard(t))


def is_active(session_id: int) -> bool:
    return session_id in _registry


async def cancel_session(session_id: int) -> SessionState | None:
    bundle = _registry.pop(session_id, None)
    if not bundle:
        logger.warning(f"[registry] cancel called for unknown session {session_id}")
        return None

    # Stop consumer — no new Tier 1 or Tier 2 tasks will spawn after this
    bundle.consumer_task.cancel()
    await asyncio.gather(bundle.consumer_task, return_exceptions=True)
    logger.info(f"[registry] consumer task cancelled for session {session_id}")

    # Wait for any in-flight Tier 2 tasks to finish cleanly before we read full_transcript
    if bundle.tier2_tasks:
        logger.info(
            f"[registry] waiting on {len(bundle.tier2_tasks)} in-flight tier2 tasks "
            f"for session {session_id}"
        )
        await asyncio.gather(*bundle.tier2_tasks, return_exceptions=True)

    logger.info(f"[registry] session {session_id} fully torn down")
    return bundle.state