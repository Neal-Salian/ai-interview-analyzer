import logging
from fastapi import APIRouter, HTTPException
from app.db.crud import get_questions_for_session, mark_question_asked

router =APIRouter()
logger = logging.getlogger(__name__)

@router.get("/questions/{session_id}")
def get_questions(session_id: str):
    """
    Returns all suggested questions for a session ordered by creation time.
    Used by the recruiter dashboard to load question history.
    """
    try:
        questions = get_questions_for_session(session_id)
        return questions
    except Exception as e:
        logger.error(f"[questions] failed to fetch for session {session_id: {e}}")
        raise HTTPException(status_code=500, detail="failed to fetch questions")



@router.patch("/questions/{question_id}/asked")
def mark_asked(question_id: str):
    """
    Marks a question as used by the recruiter.
    Called when recruiter clicks 'Mark as asked' on the dashboard.
    """
    updated = mark_question_asked(question_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"status": "updated", "question_id": question_id}
    
        