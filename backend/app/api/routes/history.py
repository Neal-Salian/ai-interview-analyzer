"""
Interview History API — read-only endpoint for completed interviews.

GET /api/history  →  paginated, searchable, filterable list of past interviews.

Reuses existing Session/Candidate/Job/EvaluationResult models.
No new tables, DTOs, or services.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession, joinedload

from app.db.database import get_db
from app.db.models import (
    Session as InterviewSession,
    Candidate,
    Job,
    EvaluationResult,
    TranscriptChunk,
)
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


def _derive_recommendation(score: Optional[float]) -> Optional[str]:
    """Derive a human-friendly recommendation label from a numeric score."""
    if score is None:
        return None
    if score >= 80:
        return "Strong Hire"
    if score >= 60:
        return "Hire"
    if score >= 40:
        return "Consider"
    return "No Hire"


@router.get("/history")
def get_interview_history(
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
):
    """
    Return completed/processing interviews for the current recruiter.

    Supports pagination, search by candidate name, status filtering,
    job filtering, and date sorting.
    """

    # ── Base query: sessions owned by this recruiter (or unassigned) ──
    query = (
        db.query(InterviewSession)
        .options(
            joinedload(InterviewSession.candidate),
            joinedload(InterviewSession.job),
        )
        .filter(
            InterviewSession.status.in_(["completed", "processing", "cancelled", "no_show"]),
            (InterviewSession.recruiter_id == current_user.id)
            | (InterviewSession.recruiter_id.is_(None)),
        )
    )

    # ── Optional filters ──────────────────────────────────────────────
    if search and search.strip():
        search_term = f"%{search.strip().lower()}%"
        query = query.filter(
            InterviewSession.candidate_id.isnot(None),
            InterviewSession.candidate.has(
                func.lower(Candidate.name).like(search_term)
            ),
        )

    if status and status.strip():
        query = query.filter(InterviewSession.status == status.strip())

    if job_id and job_id.strip():
        query = query.filter(InterviewSession.job_id == job_id.strip())

    # ── Sorting ───────────────────────────────────────────────────────
    sort_col = func.coalesce(InterviewSession.ended_at, InterviewSession.started_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc())
    else:
        query = query.order_by(sort_col.desc())

    # ── Pagination ────────────────────────────────────────────────────
    total = query.count()
    sessions = query.offset((page - 1) * page_size).limit(page_size).all()

    # ── Pre-fetch evaluation scores for all sessions in one query ─────
    session_ids = [s.id for s in sessions]
    avg_scores: dict = {}
    if session_ids:
        score_rows = (
            db.query(
                EvaluationResult.session_id,
                func.avg(EvaluationResult.combined_score).label("avg_score"),
            )
            .filter(EvaluationResult.session_id.in_(session_ids))
            .group_by(EvaluationResult.session_id)
            .all()
        )
        avg_scores = {row.session_id: round(row.avg_score, 1) if row.avg_score else None for row in score_rows}

    # ── Pre-fetch transcript existence for all sessions ───────────────
    has_transcript: set = set()
    if session_ids:
        transcript_rows = (
            db.query(TranscriptChunk.session_id)
            .filter(TranscriptChunk.session_id.in_(session_ids))
            .distinct()
            .all()
        )
        has_transcript = {row.session_id for row in transcript_rows}

    # ── Build response ────────────────────────────────────────────────
    items = []
    for s in sessions:
        score = avg_scores.get(s.id)
        items.append(
            {
                "session_id": str(s.id),
                "candidate_name": s.candidate.name if s.candidate else "Unknown",
                "job_title": s.job.title if s.job else "Not specified",
                "interview_date": (
                    s.ended_at.isoformat()
                    if s.ended_at
                    else (s.started_at.isoformat() if s.started_at else None)
                ),
                "status": s.status,
                "overall_score": score,
                "recommendation": _derive_recommendation(score),
                "has_transcript": s.id in has_transcript,
                "has_evaluation": score is not None,
            }
        )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items,
    }
