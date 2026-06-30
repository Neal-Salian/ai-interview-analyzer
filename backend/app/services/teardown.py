import asyncio
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
      3. Run behavioral metric aggregator and store results.

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

    # Step 1.5 — Clear in-memory runtime state
    from app.runtime.manager import RuntimeManager
    RuntimeManager.clear(session_id)

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

    # Step 3 — Run behavioral metrics aggregator
    # Builds a SessionContext from all session data, runs all enabled
    # metric plugins, and stores the results in session_summary JSONB.
    try:
        from app.ml.analysis.preprocessing import build_enriched_session_context
        from app.ml.analysis.aggregator import run_all_metrics

        ctx = await build_enriched_session_context(db, session_id)
        metrics_result = await asyncio.to_thread(run_all_metrics, ctx)
        crud.write_session_summary(db, session_id, metrics_result)
        logger.info(
            f"[teardown] behavioral metrics computed for session {session_id}: "
            f"{len(metrics_result.get('metrics', []))} metric(s)"
        )
    except Exception as e:
        logger.exception(
            f"[teardown] metrics computation failed for session {session_id}: {e}"
        )
    # Notify recruiter and panel that report is ready
    from app.services.email import send_report_ready
    from app.db.models import PanelMember

    candidate_name = updated.candidate.name if updated.candidate else "Candidate"
    job_title = updated.job.title if updated.job else None

    # Recruiter
    if updated.recruiter and updated.recruiter.email:
        await send_report_ready(
            to_email=updated.recruiter.email,
            recipient_name=updated.recruiter.full_name or "Recruiter",
            candidate_name=candidate_name,
            job_title=job_title,
            session_id=str(updated.id),
        )

    # Panel members
    for member in db.query(PanelMember).filter(
        PanelMember.session_id == updated.id,
        PanelMember.notify_report == True,
    ).all():
        await send_report_ready(
            to_email=member.email,
            recipient_name=member.name,
            candidate_name=candidate_name,
            job_title=job_title,
            session_id=str(updated.id),
        )