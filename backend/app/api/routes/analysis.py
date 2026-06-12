import logging
from collections import Counter
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import SessionLocal, get_db
from app.db.models import (
    Session as InterviewSession,
    EmotionFrame,
    TranscriptChunk,
    SuggestedQuestion,
)
from app.api.deps import get_current_user
from app.ml.nlp.scorer import score_big_five, score_sentiment

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/analysis/{session_id}")
def get_analysis(
    session_id: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Full post-interview analytics for a session.
    Returns emotion breakdown, Big Five personality scores,
    overall sentiment, transcript stats, and question tracking.
    """

    # ── Validate session exists ───────────────────────────────────────────────
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # ── Fetch all data ────────────────────────────────────────────────────────
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

    questions = (
        db.query(SuggestedQuestion)
        .filter(SuggestedQuestion.session_id == session_id)
        .order_by(SuggestedQuestion.created_at.asc())
        .all()
    )

    # ── Emotion stats ─────────────────────────────────────────────────────────
    total_frames = len(emotions) or 1
    emotion_counts = Counter(e.dominant_emotion for e in emotions)
    emotion_breakdown = {
        k: round(v / total_frames * 100, 1)
        for k, v in emotion_counts.most_common()
    }
    avg_confidence = round(
        sum(e.confidence for e in emotions) / total_frames, 1
    )

    # Emotion timeline for the report chart (last 50 frames max)
    emotion_timeline = [
        {
            "dominant_emotion": e.dominant_emotion,
            "confidence": round(e.confidence, 1),
            "timestamp": e.timestamp.isoformat(),
        }
        for e in emotions[-50:]
    ]

    # ── Transcript + NLP ─────────────────────────────────────────────────────
    full_text = " ".join(t.text for t in transcripts if t.text)

    big_five = {}
    overall_sentiment = {}

    if full_text.strip():
        try:
            big_five = score_big_five(full_text)
        except Exception as e:
            logger.warning(f"[analysis] Big Five scoring failed: {e}")

        try:
            overall_sentiment = score_sentiment(full_text[:1024])
        except Exception as e:
            logger.warning(f"[analysis] Sentiment scoring failed: {e}")

    # ── Questions ─────────────────────────────────────────────────────────────
    questions_asked = [q for q in questions if q.was_asked]
    questions_list = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "triggered_by": q.triggered_by,
            "was_asked": q.was_asked,
            "created_at": q.created_at.isoformat() if q.created_at else None,
        }
        for q in questions
    ]

    # ── Duration ──────────────────────────────────────────────────────────────
    duration_minutes = None
    if session.started_at and session.ended_at:
        delta = session.ended_at - session.started_at
        duration_minutes = round(delta.total_seconds() / 60, 1)

    # ── Return ────────────────────────────────────────────────────────────────
    return {
        "session_id": session_id,
        "candidate": session.candidate.name if session.candidate else None,
        "job": session.job.title if session.job else None,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration_minutes": duration_minutes,

        # Emotion
        "emotion_breakdown": emotion_breakdown,
        "avg_confidence": avg_confidence,
        "emotion_timeline": emotion_timeline,
        "total_frames_analyzed": len(emotions),

        # Transcript
        "transcript_chunks": len(transcripts),
        "full_transcript": full_text,

        # NLP
        "big_five": big_five,
        "overall_sentiment": overall_sentiment,

        # Questions
        "questions_generated": len(questions),
        "questions_asked": len(questions_asked),
        "questions": questions_list,

        # Behavioral metrics (extensible framework — Phase 10)
        "metrics": (
            session.session_summary.get("metrics", [])
            if session.session_summary
            else []
        ),

        # Attention summary (Phase 2) — from session_summary
        "attention_summary": (
            session.session_summary.get("attention_summary")
            if session.session_summary
            else None
        ),

        # Integrity events (Phase 3) — from DB
        "integrity_events": _get_integrity_events(db, session_id),
    }


def _get_integrity_events(db: Session, session_id: str) -> list:
    """Fetch integrity events for the analysis response."""
    try:
        from app.db.models import IntegrityEvent
        events = (
            db.query(IntegrityEvent)
            .filter(IntegrityEvent.session_id == session_id)
            .order_by(IntegrityEvent.timestamp.asc())
            .all()
        )
        return [
            {
                "event_type": e.event_type,
                "severity": e.severity,
                "details": str(e.details) if e.details else "",
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in events
        ]
    except Exception:
        return []


@router.post("/analysis/{session_id}/explain")
async def explain_metric(
    session_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """
    Recruiter asks a question about a metric in the report.

    Request body: {"question": "Why was confidence high?"}
    Returns: {"answer": "...", "metric_name": "...", "evidence": [...]}
    """
    question = body.get("question", "")
    if not question:
        raise HTTPException(status_code=400, detail="Question is required")

    from app.ml.explain.report_chat import chat_about_report
    result = await chat_about_report(session_id, question, db)
    return result