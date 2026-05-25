from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Job
from pydantic import BaseModel

router = APIRouter()

class JobCreate(BaseModel):
    title: str
    raw_description: str
    seniority_level: str = None

@router.post("/jobs")
def create_job(payload: JobCreate, db: Session = Depends(get_db)):
    job = Job(
        title=payload.title,
        raw_description=payload.raw_description,
        seniority_level=payload.seniority_level
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return {"job_id": str(job.id), "title": job.title}

@router.get("/jobs")
def list_jobs(db: Session = Depends(get_db)):
    return db.query(Job).all()