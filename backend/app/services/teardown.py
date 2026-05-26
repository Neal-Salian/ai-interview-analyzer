import logging
from sqlalchemy.orm import Session as DBSession
from app.core.registry import cancel_session
from app import crud

logger = logging.getLogger(__name__)


async def teardown_session(session_id: int, db: DBSession) -> None:
    """
    Full teardown sequence for a session:
      1. Cancel consumer + wait for in-flight Tier 2 tasks (registry)
      2. Stamp ended_at and mark completed in DB
      3. Return — LLM summary call will be wired here in Day 2-3
    """
    logger.info(f"[teardown] starting teardown for session {session_id}")

    # Step 1 — cancel asyncio tasks, get final state back
    session_state = await cancel_session(session_id)

    if session_state is None:
        logger.warning(
            f"[teardown] no active session found in registry for {session_id}, "
            f"updating DB only"
        )

    # Step 2 — mark DB record completed
    updated = crud.mark_session_completed(db, session_id)
    if not updated:
        logger.error(f"[teardown] session {session_id} not found in DB")
        return

    logger.info(
        f"[teardown] session {session_id} marked completed at {updated.ended_at}"
    )

    # Step 3 — LLM session summary goes here in Day 2-3
    # summary = await generate_session_summary(session_state.full_transcript)
    # crud.write_session_summary(db, session_id, summary)