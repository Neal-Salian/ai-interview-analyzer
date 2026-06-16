"""
Metric aggregator — runs all enabled metrics and produces a unified result.

Called during session teardown (or on-demand for re-computation).
Each metric runs in its own try/except so a single failure never crashes
the entire analysis pipeline.

Output format:
{
    "metrics": [
        {"name": "Confidence", "score": 78, "level": "Strong", ...},
        {"name": "Engagement", "score": 65, "level": "Strong", ...},
        ...
    ]
}
"""

import logging
from sqlalchemy.orm import Session as DBSession

from .interfaces import MetricResult, SessionContext
from .registry import get_enabled_metrics, discover_metrics

logger = logging.getLogger(__name__)


def build_session_context(db: DBSession, session_id: str) -> SessionContext:
    """
    Build a SessionContext from DB data for a given session.

    Queries all relevant tables and assembles the read-only data bag
    that every metric receives. This runs in a thread via asyncio.to_thread()
    from the teardown service.
    """
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
        logger.warning(f"[aggregator] Session {session_id} not found")
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

    # Attention events — will be populated when Phase 2 is implemented
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
        # AttentionEvent table doesn't exist yet — that's fine
        pass

    # Integrity events — will be populated when Phase 3 is implemented
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
        # IntegrityEvent table doesn't exist yet — that's fine
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


def run_all_metrics(ctx: SessionContext) -> dict:
    """
    Execute all enabled metrics and return the standardized result dict.

    Each metric runs independently — one failure does not affect others.
    Returns {
        "metrics": [MetricResult.to_dict(), ...],
        "overall_confidence": float,
        "data_quality": {...},
    }
    """
    discover_metrics()  # ensure all modules are imported

    results: list[dict] = []
    enabled = get_enabled_metrics()

    logger.info(
        f"[aggregator] Running {len(enabled)} metric(s) "
        f"for session {ctx.session_id}"
    )

    for metric in enabled:
        try:
            result: MetricResult = metric.compute(ctx)
            results.append(result.to_dict())
            logger.debug(
                f"[aggregator] {metric.name}: "
                f"{result.score}/100 ({result.level}) "
                f"[confidence={result.confidence:.2f}]"
            )
        except Exception as e:
            logger.warning(
                f"[aggregator] Metric '{metric.name}' failed: {e}",
                exc_info=True,
            )
            # Return a graceful fallback — don't crash the whole pipeline
            results.append({
                "name": metric.name,
                "score": 0,
                "raw_score": 0,
                "level": "Unavailable",
                "confidence": 0.0,
                "confidence_details": [],
                "evidence": [],
                "explanation": f"Metric computation failed: {e}",
                "signals_used": [],
            })

    # ── Compute overall confidence ───────────────────────────────────────
    confidences = [
        r.get("confidence", 0.0) for r in results
        if r.get("level") != "Unavailable"
    ]
    overall_confidence = (
        round(sum(confidences) / len(confidences), 3)
        if confidences else 0.0
    )

    # ── Data quality summary ─────────────────────────────────────────────
    word_count = len(ctx.full_transcript.split()) if ctx.full_transcript else 0
    data_quality = {
        "emotion_frames": len(ctx.emotions),
        "transcript_words": word_count,
        "transcript_chunks": len(ctx.transcripts),
        "attention_events": len(ctx.attention_events),
        "integrity_events": len(ctx.integrity_events),
        "duration_minutes": ctx.duration_minutes,
        "signals_quality": _classify_data_quality(
            emotion_frames=len(ctx.emotions),
            transcript_words=word_count,
            attention_events=len(ctx.attention_events),
        ),
    }

    logger.info(
        f"[aggregator] Completed: {len(results)} metric(s) computed "
        f"for session {ctx.session_id} "
        f"[overall_confidence={overall_confidence}]"
    )

    return {
        "metrics": results,
        "overall_confidence": overall_confidence,
        "data_quality": data_quality,
    }


def _classify_data_quality(
    emotion_frames: int,
    transcript_words: int,
    attention_events: int,
) -> str:
    """
    Classify overall data quality as high/medium/low.

    Used by the report to display a data quality badge.
    """
    score = 0
    if emotion_frames >= 50:
        score += 2
    elif emotion_frames >= 10:
        score += 1
    if transcript_words >= 200:
        score += 2
    elif transcript_words >= 50:
        score += 1
    if attention_events >= 30:
        score += 2
    elif attention_events >= 5:
        score += 1

    if score >= 5:
        return "high"
    if score >= 3:
        return "medium"
    return "low"

