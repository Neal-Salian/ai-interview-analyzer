from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DBSession
from app.db.database import get_db
from app.db.crud import get_todays_sessions

router = APIRouter()

@router.get("/sessions/today")
def todays_sessions(db: DBSession = Depends(get_db)):
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