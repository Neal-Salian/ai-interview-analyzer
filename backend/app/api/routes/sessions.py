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

router = APIRouter()
logger = logging.getLogger(__name__)


class SessionCreate(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    scheduled_at: Optional[str] = None


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
    return {
        "session_id": str(session.id),
        "candidate": session.candidate.name if session.candidate else None,
        "job": session.job.title if session.job else None,
        "status": session.status,
        "scheduled_at": session.scheduled_at,
        "started_at": session.started_at,
        "ended_at": session.ended_at,
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