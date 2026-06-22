import os
import uuid
import datetime
import logging
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import Candidate, UserRole, Session as InterviewSession, Job
from app.api.deps import get_current_user, require_recruiter

router = APIRouter()
logger = logging.getLogger(__name__)


class CandidateCreate(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    notes: Optional[str] = None
    job_id: Optional[str] = None


class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


@router.post("/candidates")
def create_candidate(
    payload: CandidateCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    existing = db.query(Candidate).filter(
        Candidate.email == payload.email
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    candidate = Candidate(
        id=uuid.uuid4(),
        recruiter_id=current_user.id,
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        notes=payload.notes,
        status="Draft",
        created_at=datetime.datetime.utcnow()
    )
    db.add(candidate)

    # Auto-create draft session
    session_id = uuid.uuid4()
    job_uuid = None
    if payload.job_id:
        try:
            job_uuid = uuid.UUID(payload.job_id)
        except ValueError:
            pass

    draft_session = InterviewSession(
        id=session_id,
        candidate_id=candidate.id,
        job_id=job_uuid,
        recruiter_id=current_user.id,
        status="draft",
        scheduled_at=None,
        started_at=None
    )
    db.add(draft_session)

    db.commit()
    db.refresh(candidate)
    logger.info(f"[candidates] created {candidate.email} by recruiter {current_user.id} and draft session {session_id}")
    return {
        "candidate_id": str(candidate.id),
        "name": candidate.name,
        "session_id": str(session_id)
    }


@router.get("/candidates")
def list_candidates(
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    query = db.query(Candidate)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Candidate.recruiter_id == current_user.id)
        
    candidates = query.order_by(Candidate.created_at.desc()).all()
    
    result = []
    for c in candidates:
        applied_jobs = [s.job.title for s in c.sessions if s.job]
        result.append({
            "id": str(c.id),
            "name": c.name,
            "email": c.email,
            "phone": c.phone,
            "status": c.status or "Draft",
            "applied_jobs": list(set(applied_jobs)),
            "created_at": c.created_at.isoformat()
        })
    return result


@router.get("/candidates/{candidate_id}")
def get_candidate(
    candidate_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if current_user.role != UserRole.ADMIN and candidate.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this candidate")

    applied_jobs = []
    session_history = []
    
    for s in candidate.sessions:
        if s.job:
            applied_jobs.append({"id": str(s.job.id), "title": s.job.title})
        session_history.append({
            "session_id": str(s.id),
            "status": s.status,
            "scheduled_at": s.scheduled_at,
            "started_at": s.started_at,
            "ended_at": s.ended_at,
            "job": s.job.title if s.job else None
        })

    # Unique jobs
    unique_jobs = {j["id"]: j for j in applied_jobs}.values()

    return {
        "id": str(candidate.id),
        "name": candidate.name,
        "email": candidate.email,
        "phone": candidate.phone,
        "notes": candidate.notes,
        "status": candidate.status or "Draft",
        "resume_url": candidate.resume_url,
        "created_at": candidate.created_at.isoformat(),
        "applied_jobs": list(unique_jobs),
        "session_history": session_history
    }


@router.patch("/candidates/{candidate_id}")
def update_candidate(
    candidate_id: str,
    payload: CandidateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if current_user.role != UserRole.ADMIN and candidate.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this candidate")

    if payload.name is not None:
        candidate.name = payload.name
    if payload.email is not None:
        # Check uniqueness
        if payload.email != candidate.email:
            existing = db.query(Candidate).filter(Candidate.email == payload.email).first()
            if existing:
                raise HTTPException(status_code=400, detail="Email already used")
        candidate.email = payload.email
    if payload.phone is not None:
        candidate.phone = payload.phone
    if payload.notes is not None:
        candidate.notes = payload.notes
    if payload.status is not None:
        candidate.status = payload.status

    db.commit()
    db.refresh(candidate)
    
    return {"status": "success", "candidate_id": str(candidate.id)}


@router.post("/candidates/{candidate_id}/resume")
def upload_resume(
    candidate_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
        
    if current_user.role != UserRole.ADMIN and candidate.recruiter_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this candidate")

    allowed_types = ["application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"]
    if file.content_type not in allowed_types:
        if not (file.filename.endswith(".pdf") or file.filename.endswith(".docx")):
            raise HTTPException(status_code=400, detail="Only PDF and DOCX files are allowed")

    upload_dir = "uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    ext = ".pdf" if file.filename.endswith(".pdf") else ".docx"
    safe_filename = f"resume_{candidate.id}{ext}"
    file_path = os.path.join(upload_dir, safe_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    candidate.resume_url = f"/api/uploads/{safe_filename}"
    db.commit()
    
    return {"status": "success", "resume_url": candidate.resume_url}