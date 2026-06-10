"""
Report chat — entry point for recruiter Q&A about interview reports.

Handles the full flow:
1. Load session_summary from DB
2. Extract relevant metric evidence
3. Build evidence-constrained prompt
4. Call Ollama for explanation
5. Return structured response

Called from the POST /analysis/{session_id}/explain endpoint.
"""

import logging
from sqlalchemy.orm import Session as DBSession

from app.ml.explain.context_builder import build_explanation_context
from app.ml.explain.explanation_engine import generate_explanation

logger = logging.getLogger(__name__)


async def chat_about_report(
    session_id: str,
    question: str,
    db: DBSession,
) -> dict:
    """
    Answer a recruiter's question about an interview report.

    Args:
        session_id: UUID string
        question: recruiter's question text
        db: SQLAlchemy session

    Returns:
        {
            "answer": str,
            "metric_name": str | None,
            "evidence": list,
            "question": str,
        }
    """
    from app.db.models import Session as InterviewSession

    # Load session with summary
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    if not session:
        return {
            "answer": "Session not found.",
            "metric_name": None,
            "evidence": [],
            "question": question,
        }

    summary = session.session_summary
    if not summary:
        return {
            "answer": "No analysis data available for this session yet. "
                      "The interview may still be in progress or the analysis "
                      "hasn't been computed.",
            "metric_name": None,
            "evidence": [],
            "question": question,
        }

    # Get transcript excerpt for context
    from app.db.models import TranscriptChunk
    transcripts = (
        db.query(TranscriptChunk)
        .filter(TranscriptChunk.session_id == session_id)
        .order_by(TranscriptChunk.timestamp.asc())
        .limit(10)
        .all()
    )
    transcript_excerpt = " ".join(t.text for t in transcripts if t.text)

    # Build context and generate explanation
    context = build_explanation_context(
        question=question,
        session_summary=summary,
        transcript_excerpt=transcript_excerpt,
    )

    answer = await generate_explanation(context["prompt"])

    # Extract evidence for the matched metric
    evidence = []
    if context["has_evidence"]:
        from app.ml.explain.evidence_extractor import extract_evidence_for_metric
        result = extract_evidence_for_metric(context["metric_name"], summary)
        if result:
            evidence = result["evidence"]

    return {
        "answer": answer,
        "metric_name": context["metric_name"],
        "evidence": evidence,
        "question": question,
    }
