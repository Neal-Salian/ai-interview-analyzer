import uuid
import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session as DBSession
from sqlalchemy import or_
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import Session as InterviewSession, Candidate, Job
from app.api.deps import get_current_user, get_owned_session
from app.services.teardown import teardown_session
from app.core.logging_config import log_event
from app.core.config import settings
import httpx
import asyncio
from app.runtime.manager import RuntimeManager
router = APIRouter()
logger = logging.getLogger(__name__)


class SessionCreate(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    scheduled_at: Optional[str] = None


class SessionJobUpdate(BaseModel):
    job_id: str



class SessionSchedule(BaseModel):
    scheduled_at: str
    interview_type: Optional[str] = None
    notes: Optional[str] = None


@router.get("/sessions/today")
def todays_sessions(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    today_start = datetime.datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    sessions = db.query(InterviewSession).filter(
        or_(
            InterviewSession.scheduled_at >= today_start,
            InterviewSession.started_at >= today_start
        ),
        InterviewSession.status != "draft",
        InterviewSession.recruiter_id == current_user.id
    ).all()
    def get_status(s: InterviewSession) -> str:
        if s.status in ["completed", "cancelled", "no_show"]:
            return s.status
        if s.ended_at is not None:
            if s.session_summary is not None:
                return "completed"
            return "processing"
        return s.status

    return [
        {
            "session_id": str(s.id),
            "candidate": s.candidate.name if s.candidate else None,
            "job": s.job.title if s.job else None,
            "job_id": str(s.job_id) if s.job_id else None,
            "scheduled_at": s.scheduled_at,
            "status": get_status(s),
            "zoom_meeting_id": s.zoom_meeting_id,
            "zoom_join_url": s.zoom_join_url,
        }
        for s in sessions
    ]


@router.post("/sessions")
def create_session(
    payload: SessionCreate,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    candidate = db.query(Candidate).filter(
        Candidate.id == payload.candidate_id
    ).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")

    job = None
    if payload.job_id:
        job = db.query(Job).filter(Job.id == payload.job_id).first()
        if not job:
            raise HTTPException(status_code=404, detail="Job not found")

    scheduled_at = None
    if payload.scheduled_at:
        scheduled_at = datetime.datetime.fromisoformat(payload.scheduled_at)

    session = InterviewSession(
        id=uuid.uuid4(),
        candidate_id=candidate.id,
        job_id=job.id if job else None,
        recruiter_id=current_user.id,  # stamp ownership at creation
        status="scheduled",
        scheduled_at=scheduled_at or datetime.datetime.utcnow(),
        started_at=None,
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Fire-and-forget notification emails
    from app.services.email import send_candidate_invite, send_recruiter_session_confirmation

    scheduled_str = session.scheduled_at.strftime("%A %d %B %Y, %H:%M") if session.scheduled_at else "TBD"

    background_tasks.add_task(
        send_candidate_invite,
        to_email=candidate.email,
        candidate_name=candidate.name,
        job_title=job.title if job else None,
        scheduled_at=scheduled_str,
    )

    background_tasks.add_task(
        send_recruiter_session_confirmation,
        to_email=current_user.email,
        recruiter_name=current_user.full_name or "Recruiter",
        candidate_name=candidate.name,
        job_title=job.title if job else None,
        scheduled_at=scheduled_str,
        session_id=str(session.id),
    )

    logger.info(f"[sessions] created session {session.id} for {candidate.name}")
    log_event(logger, "session_scheduled",
              session_id=str(session.id), candidate_name=candidate.name)
    return {
        "session_id": str(session.id),
        "candidate": candidate.name,
        "job": job.title if job else None,
        "status": session.status,
        "scheduled_at": session.scheduled_at.isoformat(),
    }
    


@router.get("/sessions/{session_id}")
def get_session(
    session: InterviewSession = Depends(get_owned_session),
):
    # Try to fetch interview_type and notes from session_summary
    interview_type = None
    notes = None
    if session.session_summary:
        interview_type = session.session_summary.get("interview_type")
        notes = session.session_summary.get("notes")

    return {
        "session_id": str(session.id),
        "candidate": session.candidate.name if session.candidate else None,
        "job": session.job.title if session.job else None,
        "status": session.status,
        "scheduled_at": session.scheduled_at,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
        "interview_type": interview_type,
        "notes": notes,
        "zoom_meeting_id": session.zoom_meeting_id,
        "zoom_join_url": session.zoom_join_url,
        "meeting_provider": session.meeting_provider,
    }


@router.get("/sessions/{session_id}/zoom")
def get_session_zoom(
    session: InterviewSession = Depends(get_owned_session),
):
    """
    Returns Zoom meeting details for an owned session.
    Only the session owner (recruiter) or admin can access this.
    The zoom_start_url is the host URL and must never be exposed to candidates.
    """
    if not session.zoom_meeting_id:
        raise HTTPException(
            status_code=404,
            detail="This session does not have an associated Zoom meeting.",
        )

    return {
        "session_id": str(session.id),
        "zoom_meeting_id": session.zoom_meeting_id,
        "zoom_start_url": session.zoom_start_url,
        "zoom_join_url": session.zoom_join_url,
        "meeting_provider": session.meeting_provider,
    }


@router.patch("/sessions/{session_id}/start")
async def start_session(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled sessions can be started")

    session.status = "active"
    session.started_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)

    logger.info(f"[sessions] started session {session.id}")
    return {
        "session_id": str(session.id),
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None
    }


@router.patch("/sessions/{session_id}/end")
async def end_session(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    await teardown_session(session_id=str(session.id), db=db)

    logger.info(f"[sessions] manually ended session {session.id}")
    return {"session_id": str(session.id), "status": "completed"}


@router.patch("/sessions/{session_id}/cancel")
async def cancel_session(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status in ["completed", "processing"]:
        raise HTTPException(status_code=400, detail="Completed interviews cannot be cancelled or marked as no-show.")
    if session.status != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled sessions can be cancelled")

    session.status = "cancelled"
    session.ended_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)

    logger.info(f"[sessions] cancelled session {session.id}")
    return {"session_id": str(session.id), "status": session.status}


@router.patch("/sessions/{session_id}/no_show")
async def no_show_session(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status in ["completed", "processing"]:
        raise HTTPException(status_code=400, detail="Completed interviews cannot be cancelled or marked as no-show.")
    if session.status not in ["scheduled", "active"]:
        raise HTTPException(status_code=400, detail="Session cannot be marked as no-show from its current status")

    session.status = "no_show"
    session.ended_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)

    logger.info(f"[sessions] marked session {session.id} as no-show")
    return {"session_id": str(session.id), "status": session.status}


@router.patch("/sessions/{session_id}/job")
async def update_session_job(
    payload: SessionJobUpdate,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft sessions can be edited")
        
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    # Admin bypass for testing, otherwise check ownership
    from app.db.models import UserRole
    if job.recruiter_id and job.recruiter_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized to use this job")
    if job.is_archived:
        raise HTTPException(status_code=400, detail="Cannot assign archived job")
        
    session.job_id = job.id
    db.commit()
    db.refresh(session)
    
    logger.info(f"[sessions] updated job for draft session {session.id} to {job.id}")
    return {"session_id": str(session.id), "job_id": str(job.id), "job": job.title}



@router.patch("/sessions/{session_id}/schedule")
async def schedule_session(
    payload: SessionSchedule,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft sessions can be scheduled")

    scheduled_at = datetime.datetime.fromisoformat(payload.scheduled_at)
    if scheduled_at.tzinfo is not None:
        scheduled_at = scheduled_at.astimezone(datetime.timezone.utc).replace(tzinfo=None)
    else:
        import zoneinfo
        tz = zoneinfo.ZoneInfo("Asia/Kolkata")
        scheduled_at = scheduled_at.replace(tzinfo=tz).astimezone(datetime.timezone.utc).replace(tzinfo=None)
    
    # We allow minor leeway (e.g., 5 minutes) for scheduling if needed, or strict 'in the past' check.
    if scheduled_at < datetime.datetime.utcnow() - datetime.timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Cannot schedule session in the past")

    # ── Create Meeting ──────────────────────────────────────────────
    from app.core.providers import get_meeting_provider, ProviderError, ProviderAuthError

    provider_type = "mock" if settings.ENV == "development" else "zoom"
    provider = get_meeting_provider(provider_type)

    candidate = session.candidate
    job = session.job
    topic = f"Interview — {candidate.name if candidate else 'Candidate'}"
    if job:
        topic += f" — {job.title}"

    try:
        meeting_result = await provider.create_meeting(
            recruiter_id=str(current_user.id),
            db=db,
            topic=topic,
            start_time=scheduled_at.isoformat() + "Z",
            duration_minutes=45,
        )
    except ProviderAuthError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ProviderError as e:
        logger.error(
            "[sessions] Meeting creation failed for session %s: %s",
            session.id, e,
        )
        raise HTTPException(
            status_code=502,
            detail="Failed to create meeting. The session remains in draft state. Please try again.",
        )
    except Exception as e:
        logger.error(
            "[sessions] unexpected error creating meeting for session %s: %s",
            session.id, e,
        )
        raise HTTPException(
            status_code=502,
            detail="Meeting service unavailable. The session remains in draft state.",
        )

    # ── Populate session fields ──────────────────────────────────────────
    session.zoom_meeting_id = meeting_result.meeting_id
    session.zoom_join_url = meeting_result.join_url
    session.zoom_start_url = meeting_result.start_url
    session.zoom_password = meeting_result.password
    session.meeting_provider = provider_type
    session.status = "scheduled"
    session.scheduled_at = scheduled_at
    
    # Update summary with interview type and notes
    # To properly update a JSONB column in SQLAlchemy without JSON functions, we can assign a new dict
    current_summary = dict(session.session_summary) if session.session_summary else {}
    if payload.interview_type:
        current_summary["interview_type"] = payload.interview_type
    if payload.notes:
        current_summary["notes"] = payload.notes
    session.session_summary = current_summary

    # ── Commit with orphan cleanup on failure ────────────────────────────
    try:
        db.commit()
        db.refresh(session)
    except Exception as commit_err:
        db.rollback()
        logger.error(
            "[sessions] DB commit failed after meeting creation for "
            "session %s, meeting %s: %s",
            session.id, meeting_result.meeting_id, commit_err,
        )
        # Attempt to clean up the orphan meeting
        async def _cleanup_orphan_meeting(rec_id: str, m_id: str, prov_type: str):
            if prov_type == "zoom":
                from app.services.zoom_api import zoom_api
                from app.db.database import SessionLocal
                bg_db = SessionLocal()
                try:
                    await zoom_api.delete_meeting(recruiter_id=rec_id, db=bg_db, meeting_id=m_id)
                finally:
                    bg_db.close()
                
        background_tasks.add_task(_cleanup_orphan_meeting, str(current_user.id), meeting_result.meeting_id, provider_type)
        raise HTTPException(
            status_code=500,
            detail="Failed to save session. The meeting is being cleaned up.",
        )

    # ── Fire-and-forget notification emails ──────────────────────────────
    from app.services.email import send_candidate_invite, send_recruiter_session_confirmation

    scheduled_str = session.scheduled_at.strftime("%A %d %B %Y, %H:%M") if session.scheduled_at else "TBD"

    if candidate:
        background_tasks.add_task(
            send_candidate_invite,
            to_email=candidate.email,
            candidate_name=candidate.name,
            job_title=job.title if job else None,
            scheduled_at=scheduled_str,
            zoom_link=session.zoom_join_url,
        )

        background_tasks.add_task(
            send_recruiter_session_confirmation,
            to_email=current_user.email,
            recruiter_name=current_user.full_name or "Recruiter",
            candidate_name=candidate.name,
            job_title=job.title if job else None,
            scheduled_at=scheduled_str,
            session_id=str(session.id),
            zoom_start_url=session.zoom_start_url,
        )

    logger.info(f"[sessions] scheduled draft session {session.id} for {candidate.name if candidate else 'unknown'}")
    log_event(logger, "session_scheduled",
              session_id=str(session.id),
              candidate_name=candidate.name if candidate else "unknown")
    return {
        "session_id": str(session.id),
        "status": session.status,
        "scheduled_at": session.scheduled_at.isoformat(),
        "zoom_join_url": session.zoom_join_url,
    }


@router.delete("/sessions/{session_id}")
async def delete_session(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.status != "draft":
        raise HTTPException(status_code=400, detail="Only draft sessions can be deleted")
    
    db.delete(session)
    db.commit()
    
    logger.info(f"[sessions] deleted draft session {session.id}")
    return {"status": "deleted"}


@router.get("/sessions/{session_id}/runtime-status")
def get_session_runtime_status(
    session: InterviewSession = Depends(get_owned_session),
):
    db_runtime = session.ai_runtime_status or "not_initialized"
    manager_status = RuntimeManager.get_status(str(session.id))
    manager_runtime = manager_status.get("status", "not_initialized")
    
    # RuntimeManager is the source of truth for in-flight transitions.
    # Use its status if it reflects a more advanced state than the DB.
    # This handles the race where the background task updates RuntimeManager
    # before committing to DB (e.g., starting_rtmp → running).
    runtime = manager_runtime if manager_runtime in ("starting_rtmp", "running", "failed") else db_runtime

    # Merge DB status with transient initialization status
    return {
        "runtime": runtime,
        "progress": manager_status.get("progress", 0),
        "current_step": manager_status.get("current_step", ""),
        "failed_component": manager_status.get("failed_component"),
        "duration_ms": manager_status.get("duration_ms"),
        "checks": manager_status.get("checks", {
            "rtmp": False,
            "ollama": False,
            "whisper": False,
            "deepface": False,
            "websocket": False
        }),
        "message": f"AI engine {runtime}."
    }




@router.post("/sessions/{session_id}/initialize-ai")
def initialize_ai(
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    session: InterviewSession = Depends(get_owned_session),
):
    if session.ai_runtime_status == "failed":
        log_event(logger, "runtime_retry_requested", session_id=str(session.id))
        
    session.ai_runtime_status = "initializing"
    db.commit()
    db.refresh(session)
    
    RuntimeManager.set_initializing(str(session.id))
    log_event(logger, "runtime_initializing", session_id=str(session.id))
    
    background_tasks.add_task(RuntimeManager.initialize_session, str(session.id))
    
    return {
        "runtime": session.ai_runtime_status,
        "message": "AI engine initialization started."
    }


@router.post("/sessions/{session_id}/start-analysis")
async def start_analysis(
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    session: InterviewSession = Depends(get_owned_session),
):
    log_event(logger, "analysis_start_requested",
              session_id=str(session.id), recruiter_id=str(current_user.id))

    if session.status != "active":
        raise HTTPException(status_code=400, detail="Session must be active (Meeting Live) to start analysis.")

    runtime = session.ai_runtime_status or "not_initialized"
    if runtime != "ready":
        raise HTTPException(
            status_code=400,
            detail=f"AI runtime must be READY to start analysis. Current state: {runtime}",
        )

    # Persist intermediate DB status so polling picks it up immediately.
    # Do NOT touch RuntimeManager._state here — start_analysis() owns
    # its own state transitions and will check for "ready".
    session.ai_runtime_status = "starting_rtmp"
    db.commit()
    db.refresh(session)

    # Run the actual RTMP startup in the background so the HTTP response
    # returns immediately.  The frontend will poll runtime-status and
    # pick up the transition to RUNNING or FAILED.
    async def _run_start_analysis():
        from app.db.database import SessionLocal
        from app.db.models import Session as InterviewSessionModel
        bg_db = SessionLocal()
        try:
            bg_session = bg_db.query(InterviewSessionModel).filter(
                InterviewSessionModel.id == str(session.id)
            ).first()
            await RuntimeManager.start_analysis(
                str(session.id),
                db=bg_db,
                session_model=bg_session,
                recruiter_id=str(current_user.id),
            )
        except Exception as e:
            logger.error(f"Background start_analysis error: {e}")
        finally:
            bg_db.close()

    asyncio.create_task(_run_start_analysis())

    return {
        "runtime": "starting_rtmp",
        "message": "RTMP consumer starting. Poll runtime-status for updates."
    }

@router.get("/sessions/mock/{mock_id}")
def get_mock_session(
    mock_id: str,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if settings.ENV != "development":
        raise HTTPException(status_code=404, detail="Not Found")
        
    session = db.query(InterviewSession).filter(
        InterviewSession.zoom_meeting_id == mock_id,
        InterviewSession.recruiter_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Mock session not found")
        
    return {
        "session_id": str(session.id),
        "status": session.status,
        "stream_key": mock_id,
        "meeting_id": mock_id,
        "rtmp_server": f"{settings.RTMP_SERVER_URL}/stream"
    }


@router.post("/sessions/mock/{session_id}/start")
async def start_mock_session(
    session_id: str,
    background_tasks: BackgroundTasks,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    if settings.ENV != "development":
        raise HTTPException(status_code=404, detail="Not Found")

    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id,
        InterviewSession.recruiter_id == current_user.id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.services.lifecycle import activate_session_and_initialize_ai
    activate_session_and_initialize_ai(
        session, db, background_tasks, trigger="mock_meeting.started"
    )

    return {
        "message": "Mock session started",
        "session_id": str(session.id),
    }