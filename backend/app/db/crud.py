import uuid
import datetime
from sqlalchemy.orm import Session as DBSession

from app.db.database import SessionLocal
from app.db.models import (
    EmotionFrame,
    TranscriptChunk,
    Job,
    Session as InterviewSession,
    Candidate,
)


# ── Stream pipeline writes ────────────────────────────────────────────────────

def save_emotion(session_id: str, emotion: dict):
    db = SessionLocal()
    try:
        frame = EmotionFrame(
            id=uuid.uuid4(),
            session_id=session_id,
            dominant_emotion=emotion["dominant_emotion"],
            confidence=emotion["confidence"],
            timestamp=datetime.datetime.utcnow()
        )
        db.add(frame)
        db.commit()
    finally:
        db.close()


def save_transcript(session_id: str, text: str):
    db = SessionLocal()
    try:
        chunk = TranscriptChunk(
            id=uuid.uuid4(),
            session_id=session_id,
            text=text,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(chunk)
        db.commit()
    finally:
        db.close()


# ── Job helpers ───────────────────────────────────────────────────────────────

def create_job(title: str, raw_description: str, seniority_level: str = None):
    db = SessionLocal()
    try:
        job = Job(
            id=uuid.uuid4(),
            title=title,
            raw_description=raw_description,
            seniority_level=seniority_level
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        return job
    finally:
        db.close()


def get_job(job_id: str):
    db = SessionLocal()
    try:
        return db.query(Job).filter(Job.id == job_id).first()
    finally:
        db.close()


# ── Session helpers ───────────────────────────────────────────────────────────

def get_todays_sessions():
    db = SessionLocal()
    try:
        today = datetime.date.today()
        return db.query(InterviewSession).filter(
            InterviewSession.scheduled_at >= datetime.datetime.combine(
                today, datetime.time.min
            ),
            InterviewSession.scheduled_at <= datetime.datetime.combine(
                today, datetime.time.max
            )
        ).all()
    finally:
        db.close()


def get_session_by_meeting_id(session_id: str) -> InterviewSession | None:
    """Look up a session by zoom_meeting_id. Used by the meeting.ended webhook."""
    db = SessionLocal()
    try:
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.zoom_meeting_id == session_id)
            .first()
        )
    finally:
        db.close()


def get_session_history(session_id: str) -> dict:
    """
    Returns all emotion frames and transcript chunks for a session.
    Called on recruiter reconnect to replay missed data.
    """
    db = SessionLocal()
    try:
        emotions = (
            db.query(EmotionFrame)
            .filter(EmotionFrame.session_id == session_id)
            .order_by(EmotionFrame.timestamp.asc())
            .all()
        )
        transcripts = (
            db.query(TranscriptChunk)
            .filter(TranscriptChunk.session_id == session_id)
            .order_by(TranscriptChunk.timestamp.asc())
            .all()
        )
        return {
            "emotions": [
                {
                    "dominant_emotion": e.dominant_emotion,
                    "confidence": e.confidence,
                    "timestamp": e.timestamp.isoformat()
                }
                for e in emotions
            ],
            "transcripts": [
                {
                    "text": t.text,
                    "timestamp": t.timestamp.isoformat()
                }
                for t in transcripts
            ]
        }
    finally:
        db.close()


def get_active_sessions() -> list:
    """
    Returns all sessions currently marked active.
    Called on server startup to restart consumers that died on crash.
    """
    db = SessionLocal()
    try:
        return (
            db.query(InterviewSession)
            .filter(InterviewSession.status == "active")
            .all()
        )
    finally:
        db.close()


# ── Teardown writes ───────────────────────────────────────────────────────────

def mark_session_completed(db: DBSession, session_id: str) -> InterviewSession | None:
    """
    Stamps ended_at and flips status to completed.
    Called by teardown_session() after the consumer task is cancelled.
    Accepts an injected db session (not SessionLocal) so it participates
    in the same transaction as the webhook handler.
    """
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        return None

    session.status = "completed"
    session.ended_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session


def write_session_summary(
    db: DBSession,
    session_id: str,
    summary: dict,
) -> InterviewSession | None:
    """
    Writes the JSONB session_summary field.
    Kept separate from mark_session_completed so it can be called
    later once the LLM summary is ready (Day 2-3).
    """
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.id == session_id)
        .first()
    )
    if not session:
        return None

    session.session_summary = summary
    db.commit()
    db.refresh(session)
    return session

    # ── Questions ─────────────────────────────────────────────────────────────────

def save_question(session_id: str, question_text: str, triggered_by: str) -> str:
    """
    Saves a single suggested question to the DB.
    Returns the question UUID so it can be broadcast over WebSocket.
    """
    db = SessionLocal()
    try:
        from app.db.models import SuggestedQuestion
        question_id = uuid.uuid4()
        q = SuggestedQuestion(
            id=question_id,
            session_id=session_id,
            question_text=question_text,
            triggered_by=triggered_by,
            was_asked=False,
            created_at=datetime.datetime.utcnow()
        )
        db.add(q)
        db.commit()
        return str(question_id)
    finally:
        db.close()


def get_questions_for_session(session_id: str) -> list:
    """
    Returns all suggested questions for a session ordered by creation time.
    """
    db = SessionLocal()
    try:
        from app.db.models import SuggestedQuestion
        questions = (
            db.query(SuggestedQuestion)
            .filter(SuggestedQuestion.session_id == session_id)
            .order_by(SuggestedQuestion.created_at.asc())
            .all()
        )
        return [
            {
                "id": str(q.id),
                "question_text": q.question_text,
                "triggered_by": q.triggered_by,
                "was_asked": q.was_asked,
                "created_at": q.created_at.isoformat()
            }
            for q in questions
        ]
    finally:
        db.close()


def mark_question_asked(question_id: str) -> bool:
    """
    Flips was_asked to True for a question.
    Returns True if found and updated, False if not found.
    """
    db = SessionLocal()
    try:
        from app.db.models import SuggestedQuestion
        q = db.query(SuggestedQuestion).filter(
            SuggestedQuestion.id == question_id
        ).first()
        if not q:
            return False
        q.was_asked = True
        db.commit()
        return True
    finally:
        db.close()