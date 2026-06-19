import uuid
import logging
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from app.db.database import get_db
from app.db.models import Job, UserRole
from app.api.deps import get_current_user, require_recruiter

router = APIRouter()
logger = logging.getLogger(__name__)


class JobCreate(BaseModel):
    title: str
    raw_description: str
    seniority_level: Optional[str] = None


@router.post("/jobs")
def create_job(
    payload: JobCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    job = Job(
        recruiter_id=current_user.id,
        title=payload.title,
        raw_description=payload.raw_description,
        seniority_level=payload.seniority_level
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": str(job.id), "title": job.title}


@router.get("/jobs")
def list_jobs(
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    query = db.query(Job)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Job.recruiter_id == current_user.id)
    return query.all()