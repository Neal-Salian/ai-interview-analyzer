"""
Preprocessing pipeline Phase 0.

Builds the SessionContext from the database and runs Candidate Attribution
to separate the Candidate and Recruiter transcripts before metrics are computed.
"""

import asyncio
import logging
from sqlalchemy.orm import Session as DBSession

from app.ml.analysis.interfaces import SessionContext
from app.ml.analysis.candidate_attribution import perform_attribution

logger = logging.getLogger(__name__)


def _fetch_raw_context(db: DBSession, session_id: str) -> SessionContext:
    """Synchronous DB queries to build the base SessionContext."""
    from app.db.models import (
        Session as InterviewSession,
        EmotionFrame,
        TranscriptChunk,
        SuggestedQuestion,
    )

    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    if not session:
        logger.warning(f"[preprocessing] Session {session_id} not found")
        return SessionContext(session_id=session_id)

    # Emotions
    emotions = (
        db.query(EmotionFrame)
        .filter(EmotionFrame.session_id == session_id)
        .order_by(EmotionFrame.timestamp.asc())
        .all()
    )
    emotion_dicts = [
        {
            "dominant_emotion": e.dominant_emotion,
            "confidence": e.confidence,
            "timestamp": e.timestamp.isoformat() if e.timestamp else None,
        }
        for e in emotions
    ]

    # Transcripts
    transcripts = (
        db.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session_id)
        .order_by(TranscriptChunk.timestamp.asc())
        .all()
    )
    transcript_dicts = [
        {
            "text": t.text,
            "timestamp": t.timestamp.isoformat() if t.timestamp else None,
        }
        for t in transcripts
    ]
    full_text = " ".join(t.text for t in transcripts if t.text)

    # Questions
    questions = (
        db.query(SuggestedQuestion)
        .filter(SuggestedQuestion.session_id == session_id)
        .order_by(SuggestedQuestion.created_at.asc())
        .all()
    )
    question_dicts = [
        {
            "id": str(q.id),
            "question_text": q.question_text,
            "triggered_by": q.triggered_by,
            "was_asked": q.was_asked,
        }
        for q in questions
    ]

    # Duration
    duration = None
    if session.started_at and session.ended_at:
        delta = session.ended_at - session.started_at
        duration = round(delta.total_seconds() / 60, 1)

    # Job skills
    job_skills = []
    job_title = ""
    if session.job:
        job_title = session.job.title or ""
        job_skills = session.job.extracted_skills or []

    # Candidate name
    candidate_name = ""
    if session.candidate:
        candidate_name = session.candidate.name or ""

    # Attention events
    attention_dicts: list[dict] = []
    try:
        from app.db.models import AttentionEvent
        attention_events = (
            db.query(AttentionEvent)
            .filter(AttentionEvent.session_id == session_id)
            .order_by(AttentionEvent.timestamp.asc())
            .all()
        )
        attention_dicts = [
            {
                "direction": a.direction,
                "confidence": a.confidence,
                "timestamp": a.timestamp.isoformat() if a.timestamp else None,
            }
            for a in attention_events
        ]
    except Exception:
        pass

    # Integrity events
    integrity_dicts: list[dict] = []
    try:
        from app.db.models import IntegrityEvent
        integrity_events = (
            db.query(IntegrityEvent)
            .filter(IntegrityEvent.session_id == session_id)
            .order_by(IntegrityEvent.timestamp.asc())
            .all()
        )
        integrity_dicts = [
            {
                "event_type": ie.event_type,
                "severity": ie.severity,
                "details": ie.details,
                "timestamp": ie.timestamp.isoformat() if ie.timestamp else None,
            }
            for ie in integrity_events
        ]
    except Exception:
        pass

    return SessionContext(
        session_id=session_id,
        candidate_name=candidate_name,
        job_title=job_title,
        job_skills=job_skills,
        duration_minutes=duration,
        emotions=emotion_dicts,
        transcripts=transcript_dicts,
        full_transcript=full_text,
        attention_events=attention_dicts,
        integrity_events=integrity_dicts,
        questions=question_dicts,
    )


async def build_enriched_session_context(db: DBSession, session_id: str) -> SessionContext:
    """
    Builds the base context from DB, then performs Candidate Attribution
    to populate the candidate and recruiter separated transcripts.
    """
    logger.info(f"[preprocessing] Building context for session {session_id}")
    
    # 1. Fetch raw data from DB (in a thread to avoid blocking event loop)
    ctx = await asyncio.to_thread(_fetch_raw_context, db, session_id)
    
    # 2. Perform Phase 0 - Candidate Attribution
    logger.info(f"[preprocessing] Running candidate attribution for session {session_id}")
    attribution_result = await perform_attribution(
        full_transcript=ctx.full_transcript,
        candidate_name=ctx.candidate_name,
        job_title=ctx.job_title,
        recent_questions=ctx.questions
    )
    
    # 3. Enrich the context
    ctx.conversation_timeline = attribution_result.get("segments", [])
    
    candidate_parts = []
    recruiter_parts = []
    
    for segment in ctx.conversation_timeline:
        speaker = segment.get("speaker")
        text = segment.get("text", "").strip()
        
        if speaker == "Candidate":
            ctx.candidate_segments.append(segment)
            candidate_parts.append(text)
        elif speaker == "Recruiter":
            ctx.recruiter_segments.append(segment)
            recruiter_parts.append(text)
            
    ctx.candidate_transcript = " ".join(candidate_parts)
    ctx.recruiter_transcript = " ".join(recruiter_parts)
    
    logger.info(
        f"[preprocessing] Attribution complete. "
        f"Candidate words: {len(ctx.candidate_transcript.split())}, "
        f"Recruiter words: {len(ctx.recruiter_transcript.split())}"
    )
    
    return ctx
