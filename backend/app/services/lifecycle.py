import datetime
import logging
from sqlalchemy.orm import Session
from fastapi import BackgroundTasks
from app.db.models import Session as InterviewSession
from app.runtime.manager import RuntimeManager
from app.core.logging_config import log_event

logger = logging.getLogger(__name__)


def activate_session_and_initialize_ai(
    session: InterviewSession,
    db: Session,
    background_tasks: BackgroundTasks,
    trigger: str = "meeting.started"
):
    """
    Transitions a session to 'active' and triggers background AI initialization.
    This logic is shared between the Zoom webhook and development Mock flow.
    """
    session_id = str(session.id)
    meeting_id = str(session.zoom_meeting_id) if session.zoom_meeting_id else None
    recruiter_id_str = str(session.recruiter_id) if session.recruiter_id else None

    # ── 1. Transition Session to Active ────────────────────────────
    if session.status != "active":
        session.status = "active"
        if not session.started_at:
            session.started_at = datetime.datetime.utcnow()
        db.commit()
        db.refresh(session)
        logger.info(
            f"[{trigger}] session {session_id} transitioned to active "
            f"(candidate_id={session.candidate_id}, recruiter_id={session.recruiter_id})"
        )

    # ── 2. Trigger Automatic AI Initialization ─────────────────────
    runtime_status = RuntimeManager.get_status(session_id).get("status")
    
    # Initialization Guard
    if runtime_status not in ["initializing", "ready", "starting_rtmp", "running"]:
        RuntimeManager.set_initializing(session_id)
        session.ai_runtime_status = "initializing"
        db.commit()

        log_event(
            logger, 
            "runtime_auto_initialize_requested",
            session_id=session_id, 
            meeting_id=meeting_id, 
            recruiter_id=recruiter_id_str,
            trigger=trigger
        )

        log_event(
            logger, 
            "runtime_initializing",
            session_id=session_id, 
            meeting_id=meeting_id, 
            recruiter_id=recruiter_id_str,
            trigger=trigger
        )

        background_tasks.add_task(RuntimeManager.initialize_session, session_id)
        logger.info(f"[{trigger}] AI initialization triggered for session {session_id}")
    else:
        logger.info(f"[{trigger}] skipping AI initialization, runtime already {runtime_status}")
