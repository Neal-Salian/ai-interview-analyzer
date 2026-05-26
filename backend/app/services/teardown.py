import logging
from sqlalchemy.orm import Session as DBSession

from app.core.registry import cancel_session
from app.db import crud

logger = logging.getLogger(__name__)


async def teardown_session(session_id: str, db: DBSession) -> None:
    """
    Full teardown sequence for a completed interview session:

      1. Cancel the RTMP consumer task and wait for any in-flight
         Tier 2 tasks to finish cleanly (via registry).
      2. Stamp ended_at and flip status → completed in the DB.
      3. [Day 2-3] LLM session summary call will be wired in here.

    session_id is a UUID string, matching the rest of the codebase.
    db is injected from the webhook route so we share the same
    SQLAlchemy session and avoid opening a second connection.
    """
    logger.info(f"[teardown] starting teardown for session {session_id}")

    # Step 1 — cancel asyncio tasks; get final SessionState back
    # (full_transcript lives here, ready for the Day 2-3 summary call)
    session_state = await cancel_session(session_id)

    if session_state is None:
        # Session wasn't in the registry — server may have restarted after
        # the meeting started. Still close it out in the DB.
        logger.warning(
            f"[teardown] session {session_id} not found in registry "
            f"(server restart?), updating DB only"
        )

    # Step 2 — mark the DB record completed
    updated = crud.mark_session_completed(db, session_id)
    if not updated:
        logger.error(
            f"[teardown] session {session_id} not found in DB — "
            f"nothing to mark completed"
        )
        return

    logger.info(
        f"[teardown] session {session_id} marked completed "
        f"at {updated.ended_at}"
    )

    # Step 3 — LLM session summary (Day 2-3, uncomment when ready)
    # if session_state:
    #     summary = await generate_session_summary(session_state.full_transcript)
    #     crud.write_session_summary(db, session_id, summary)