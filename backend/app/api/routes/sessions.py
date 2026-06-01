from fastapi import APIRouter, Depends
from app.db.crud import get_todays_sessions
from app.api.deps import get_current_user

router = APIRouter()

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