import uuid
import datetime
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import Candidate
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


class CandidateCreate(BaseModel):
    name: str
    email: str


@router.post("/candidates")
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    existing = db.query(Candidate).filter(
        Candidate.email == payload.email
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    candidate = Candidate(
        id=uuid.uuid4(),
        name=payload.name,
        email=payload.email,
        created_at=datetime.datetime.utcnow()
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    logger.info(f"[candidates] created {candidate.email}")
    return {"candidate_id": str(candidate.id), "name": candidate.name}


@router.get("/candidates")
def list_candidates(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user)
):
    candidates = db.query(Candidate).order_by(Candidate.created_at.desc()).all()
    return [
        {
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "created_at": c.created_at.isoformat()
        }
        for c in candidates
    ]