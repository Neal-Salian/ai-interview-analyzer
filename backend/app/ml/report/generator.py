"""
Report generator — builds a structured 11-section interview report.

Reads from:
- Session DB record (dates, duration, candidate, job)
- session_summary JSONB (metrics, attention, integrity)
- EmotionFrame table (emotion breakdown, timeline)
- TranscriptChunk table (full transcript)
- SuggestedQuestion table (questions)

Returns a structured dict consumed by the PDF builder and API.
"""

import logging
from collections import Counter
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)


def generate_report(session_id: str, db: DBSession) -> dict:
    """
    Build the complete 11-section report for a session.

    Returns structured dict with all report sections.
    """
    from app.db.models import (
        Session as InterviewSession,
        EmotionFrame,
        TranscriptChunk,
        SuggestedQuestion,
    )

    # ── Load session ─────────────────────────────────────────────────────
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    if not session:
        return {"error": f"Session {session_id} not found"}

    # ── Load data ────────────────────────────────────────────────────────
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

    summary = session.session_summary or {}
    metrics = summary.get("metrics", [])
    overall_confidence = summary.get("overall_confidence", 0.0)
    data_quality = summary.get("data_quality", {})
    full_text = " ".join(t.text for t in transcripts if t.text)

    # Duration
    duration = None
    if session.started_at and session.ended_at:
        delta = session.ended_at - session.started_at
        duration = round(delta.total_seconds() / 60, 1)

    # Emotion stats
    total_frames = len(emotions) or 1
    emotion_counts = Counter(e.dominant_emotion for e in emotions)
    emotion_breakdown = {
        k: round(v / total_frames * 100, 1)
        for k, v in emotion_counts.most_common()
    }
    dominant_emotion = emotion_counts.most_common(1)[0][0] if emotion_counts else "neutral"
    avg_confidence = round(
        sum(e.confidence for e in emotions) / total_frames, 1
    )

    # Attention data
    attention_summary = summary.get("attention_summary", {})

    # Integrity events
    integrity_events = []
    try:
        from app.db.models import IntegrityEvent
        ie_records = (
            db.query(IntegrityEvent)
            .filter(IntegrityEvent.session_id == session_id)
            .order_by(IntegrityEvent.timestamp.asc())
            .all()
        )
        integrity_events = [
            {
                "event_type": e.event_type,
                "severity": e.severity,
                "details": str(e.details) if e.details else "",
                "timestamp": e.timestamp.isoformat() if e.timestamp else None,
            }
            for e in ie_records
        ]
    except Exception:
        pass

    # NLP scores
    big_five = {}
    overall_sentiment = {}
    if full_text.strip():
        try:
            from app.ml.nlp.scorer import score_big_five, score_sentiment
            big_five = score_big_five(full_text)
            overall_sentiment = score_sentiment(full_text[:1024])
        except Exception as e:
            logger.warning(f"[REPORT] NLP scoring failed: {e}")

    # ── Find specific metrics by name ────────────────────────────────────
    def find_metric(name: str) -> dict | None:
        for m in metrics:
            if m.get("name", "").lower() == name.lower():
                return m
        return None

    stress_metric = find_metric("Stress Indicators")
    stability_metric = find_metric("Emotional Stability")
    confidence_metric = find_metric("Confidence")
    communication_metric = find_metric("Communication")

    # ── Build report sections ────────────────────────────────────────────
    return {
        "session_id": session_id,
        "generated_at": __import__("datetime").datetime.utcnow().isoformat(),

        # Section 1: Executive Summary
        "executive_summary": {
            "candidate": session.candidate.name if session.candidate else "Unknown",
            "job": session.job.title if session.job else "Not specified",
            "duration_minutes": duration,
            "status": session.status,
            "dominant_emotion": dominant_emotion,
            "avg_confidence": avg_confidence,
            "overall_sentiment": overall_sentiment.get("label", "N/A"),
            "metrics_computed": len(metrics),
            "integrity_alerts": len(integrity_events),
            "overall_confidence": overall_confidence,
            "data_quality": data_quality.get("signals_quality", "unknown"),
        },

        # Section 2: Interview Overview
        "interview_overview": {
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
            "duration_minutes": duration,
            "total_frames": len(emotions),
            "transcript_chunks": len(transcripts),
            "questions_generated": len(questions),
            "questions_asked": len([q for q in questions if q.was_asked]),
        },

        # Section 3: Communication Analysis
        "communication_analysis": {
            "overall_sentiment": overall_sentiment,
            "big_five": big_five,
            "communication_metric": communication_metric,
            "transcript_chunks": len(transcripts),
            "word_count": len(full_text.split()) if full_text else 0,
        },

        # Section 4: Behavioral Insights
        "behavioral_insights": {
            "metrics": metrics,
            "total_metrics": len(metrics),
            "overall_confidence": overall_confidence,
        },

        # Section 5: Attention Indicators
        "attention_indicators": attention_summary,

        # Section 6: Integrity Indicators
        "integrity_indicators": {
            "events": integrity_events,
            "total_alerts": len(integrity_events),
            "severity_breakdown": Counter(
                e["severity"] for e in integrity_events
            ),
        },

        # Section 7: Stress Indicators
        "stress_indicators": stress_metric,

        # Section 8: Emotional Stability
        "emotional_stability": {
            "metric": stability_metric,
            "emotion_breakdown": emotion_breakdown,
            "dominant_emotion": dominant_emotion,
            "avg_confidence": avg_confidence,
        },

        # Section 9: Technical Summary
        "technical_summary": {
            "job_title": session.job.title if session.job else None,
            "job_skills": session.job.extracted_skills if session.job else [],
            "seniority": session.job.seniority_level if session.job else None,
            "confidence_metric": confidence_metric,
        },

        # Section 10: Evidence-Based Observations
        "evidence_observations": {
            "metrics_with_evidence": [
                {
                    "name": m.get("name"),
                    "score": m.get("score"),
                    "raw_score": m.get("raw_score", m.get("score")),
                    "level": m.get("level"),
                    "confidence": m.get("confidence", 0.0),
                    "confidence_details": m.get("confidence_details", []),
                    "evidence": m.get("evidence", []),
                    "explanation": m.get("explanation", ""),
                }
                for m in metrics
                if m.get("evidence")
            ],
        },

        # Section 11: Transcript Appendix
        "transcript_appendix": {
            "full_transcript": full_text,
            "chunk_count": len(transcripts),
            "questions": [
                {
                    "question_text": q.question_text,
                    "triggered_by": q.triggered_by,
                    "was_asked": q.was_asked,
                }
                for q in questions
            ],
        },
    }
