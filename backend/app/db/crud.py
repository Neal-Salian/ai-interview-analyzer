import uuid
import datetime
from app.db.database import SessionLocal
from app.db.models import EmotionFrame, TranscriptChunk, Job, Session, Candidate


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


def get_todays_sessions():
    db = SessionLocal()
    try:
        today = datetime.date.today()
        return db.query(Session).filter(
            Session.scheduled_at >= datetime.datetime.combine(today, datetime.time.min),
            Session.scheduled_at <= datetime.datetime.combine(today, datetime.time.max)
        ).all()
    finally:
        db.close()


def get_session_history(session_id: str) -> dict:
    """
    Returns all emotion frames and transcript chunks saved so far
    for a session. Called when a recruiter reconnects to replay
    everything they missed while disconnected.
    """
    db = SessionLocal()
    try:
        emotions = db.query(EmotionFrame)\
            .filter(EmotionFrame.session_id == session_id)\
            .order_by(EmotionFrame.timestamp.asc())\
            .all()

        transcripts = db.query(TranscriptChunk)\
            .filter(TranscriptChunk.session_id == session_id)\
            .order_by(TranscriptChunk.timestamp.asc())\
            .all()

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
    Returns all sessions currently marked as active.
    Called on server startup to restart any consumers
    that died when the server previously crashed.
    """
    db = SessionLocal()
    try:
        return db.query(Session)\
            .filter(Session.status == "active")\
            .all()
    finally:
        db.close()