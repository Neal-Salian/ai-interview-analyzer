import asyncio
import logging
from dataclasses import dataclass, field
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class SessionState:
    session_id: str                          # UUID string, matches DB
    rolling_window: deque = field(default_factory=lambda: deque(maxlen=10))
    full_transcript: str = ""
    tier2_healthy: bool = True


@dataclass
class SessionTaskBundle:
    consumer_task: asyncio.Task
    tier2_tasks: set[asyncio.Task]
    state: SessionState


# Global registry: session_id (UUID str) → SessionTaskBundle
_registry: dict[str, SessionTaskBundle] = {}


def register_session(session_id: str, consumer_task: asyncio.Task) -> None:
    state = SessionState(session_id=session_id)
    _registry[session_id] = SessionTaskBundle(
        consumer_task=consumer_task,
        tier2_tasks=set(),
        state=state,
    )
    logger.info(f"[registry] registered session {session_id}")


def get_bundle(session_id: str) -> SessionTaskBundle | None:
    return _registry.get(session_id)


def add_tier2_task(session_id: str, task: asyncio.Task) -> None:
    bundle = _registry.get(session_id)
    if bundle:
        bundle.tier2_tasks.add(task)
        task.add_done_callback(lambda t: bundle.tier2_tasks.discard(t))


def is_active(session_id: str) -> bool:
    return session_id in _registry


async def cancel_session(session_id: str) -> SessionState | None:
    bundle = _registry.pop(session_id, None)
    if not bundle:
        logger.warning(f"[registry] cancel called for unknown session {session_id}")
        return None

    # Stop the consumer — no new Tier 1 or Tier 2 tasks spawn after this
    bundle.consumer_task.cancel()
    await asyncio.gather(bundle.consumer_task, return_exceptions=True)
    logger.info(f"[registry] consumer cancelled for session {session_id}")

    # Wait for any in-flight Tier 2 tasks to finish before full_transcript is read
    if bundle.tier2_tasks:
        logger.info(
            f"[registry] waiting on {len(bundle.tier2_tasks)} "
            f"in-flight tier2 tasks for session {session_id}"
        )
        await asyncio.gather(*bundle.tier2_tasks, return_exceptions=True)

    logger.info(f"[registry] session {session_id} fully torn down")
    return bundle.state