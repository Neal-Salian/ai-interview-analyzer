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

    metrics = {
        "total_candidates": 0,
        "draft_candidates": 0,
        "scheduled_interviews": 0,
        "active_interviews": 0,
        "completed_interviews": 0,
        "cancelled_interviews": 0,
        "no_shows": 0
    }

    candidates_dict = {}
    sessions_list = []

    for s in job.sessions:
        sessions_list.append({
            "id": str(s.id),
            "candidate_name": s.candidate.name if s.candidate else None,
            "candidate_id": str(s.candidate_id) if s.candidate_id else None,
            "status": s.status,
            "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
            "interview_type": s.session_summary.get("interview_type") if s.session_summary else None,
        })
        
        if s.status == "draft":
            metrics["draft_candidates"] += 1
        elif s.status == "scheduled":
            metrics["scheduled_interviews"] += 1
        elif s.status in ["active", "processing"]:
            metrics["active_interviews"] += 1
        elif s.status == "completed":
            metrics["completed_interviews"] += 1
        elif s.status == "cancelled":
            metrics["cancelled_interviews"] += 1
        elif s.status == "no_show":
            metrics["no_shows"] += 1

        if s.candidate:
            c = s.candidate
            if str(c.id) not in candidates_dict:
                candidates_dict[str(c.id)] = {
                    "id": str(c.id),
                    "name": c.name,
                    "email": c.email,
                    "status": "Draft",
                    "created_at": c.created_at.isoformat(),
                    "sessions_status": []
                }
            candidates_dict[str(c.id)]["sessions_status"].append(s.status)

    for c_id, c in candidates_dict.items():
        s_statuses = c["sessions_status"]
        if any(st in ["scheduled", "active", "processing"] for st in s_statuses):
            c["status"] = "Scheduled"
        elif any(st == "completed" for st in s_statuses):
            c["status"] = "Completed"
        del c["sessions_status"]
        metrics["total_candidates"] += 1

    return {
        "id": str(job.id),
        "title": job.title,
        "raw_description": job.raw_description,
        "seniority_level": job.seniority_level,
        "interview_type": job.interview_type,
        "extracted_skills": job.extracted_skills,
        "is_archived": job.is_archived,
        "created_at": job.created_at.isoformat(),
        "metrics": metrics,
        "candidates": list(candidates_dict.values()),
        "sessions": sessions_list
    }


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