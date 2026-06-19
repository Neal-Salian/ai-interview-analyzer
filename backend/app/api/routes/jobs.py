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
    interview_type: Optional[str] = None
    extracted_skills: Optional[list[str]] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    raw_description: Optional[str] = None
    extracted_skills: Optional[list[str]] = None
    seniority_level: Optional[str] = None
    interview_type: Optional[str] = None


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
        seniority_level=payload.seniority_level,
        interview_type=payload.interview_type,
        extracted_skills=payload.extracted_skills
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
    query = db.query(Job).filter(Job.is_archived == False)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Job.recruiter_id == current_user.id)
    return query.all()


@router.get("/jobs/{job_id}")
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    from fastapi import HTTPException
    query = db.query(Job).filter(Job.id == job_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Job.recruiter_id == current_user.id)
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.patch("/jobs/{job_id}")
def update_job(
    job_id: str,
    payload: JobUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    from fastapi import HTTPException
    query = db.query(Job).filter(Job.id == job_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Job.recruiter_id == current_user.id)
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if payload.title != None:
        job.title = payload.title
    if payload.raw_description != None:
        job.raw_description = payload.raw_description
    if payload.extracted_skills != None:
        job.extracted_skills = payload.extracted_skills
    if payload.seniority_level != None:
        job.seniority_level = payload.seniority_level
    if payload.interview_type != None:
        job.interview_type = payload.interview_type

    db.commit()
    db.refresh(job)
    return job


@router.patch("/jobs/{job_id}/archive")
def archive_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(require_recruiter)
):
    from fastapi import HTTPException
    query = db.query(Job).filter(Job.id == job_id)
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Job.recruiter_id == current_user.id)
    job = query.first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_archived = True
    db.commit()
    db.refresh(job)
    return {"message": "Job archived successfully"}