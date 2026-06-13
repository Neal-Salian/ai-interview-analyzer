import uuid
import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.crud import get_todays_sessions
from app.db.models import Session as InterviewSession, Candidate, Job
from app.api.deps import get_current_user
from app.services.teardown import teardown_session
from app.api.routes.zoom_webhook import run_consumer_with_retry
from app.core.registry import register_session, is_active
import asyncio

router = APIRouter()
logger = logging.getLogger(__name__)


class SessionCreate(BaseModel):
    candidate_id: str
    job_id: Optional[str] = None
    scheduled_at: Optional[str] = None


@router.get("/sessions/today")
def todays_sessions(current_user=Depends(get_current_user)):
    sessions = get_todays_sessions()
    return [
        {
            "session_id": str(s.id),
            "candidate": s.candidate.name if s.candidate else None,
            "job": s.job.title if s.job else None,
            "scheduled_at": s.scheduled_at,
            "status": s.status
        }
        for s in sessions
    ]


@router.post("/sessions")
def create_session(
    payload: SessionCreate,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user)
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
        status="scheduled",
        scheduled_at=scheduled_at or datetime.datetime.utcnow(),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    logger.info(f"[sessions] created session {session.id} for {candidate.name}")
    return {
        "session_id": str(session.id),
        "candidate": candidate.name,
        "job": job.title if job else None,
        "status": session.status,
        "scheduled_at": session.scheduled_at.isoformat()
    }


@router.get("/sessions/{session_id}")
def get_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return {
        "session_id": str(session.id),
        "candidate": session.candidate.name if session.candidate else None,
        "job": session.job.title if session.job else None,
        "status": session.status,
        "scheduled_at": session.scheduled_at,
        "started_at": session.started_at,
        "ended_at": session.ended_at
    }


@router.patch("/sessions/{session_id}/start")
async def start_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status != "scheduled":
        raise HTTPException(status_code=400, detail="Only scheduled sessions can be started")

    session.status = "active"
    session.started_at = datetime.datetime.utcnow()
    db.commit()

    if not is_active(session_id):
        rtmp_url = f"rtmp://localhost:1935/stream/{session_id}"
        consumer_task = asyncio.create_task(run_consumer_with_retry(session_id, rtmp_url))
        register_session(session_id, consumer_task)
        logger.info(f"[sessions] spawned consumer for session {session_id}")

    logger.info(f"[sessions] started session {session_id}")
    return {"session_id": session_id, "status": "active"}


@router.patch("/sessions/{session_id}/end")
async def end_session(
    session_id: str,
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user)
):
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.status == "completed":
        raise HTTPException(status_code=400, detail="Session already completed")

    await teardown_session(session_id, db)

    logger.info(f"[sessions] ended session {session_id}")
    return {"session_id": session_id, "status": "completed"}