import logging
from fastapi import APIRouter, HTTPException, Depends
from app.db.crud import get_questions_for_session, mark_question_asked
from app.api.deps import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/questions/{session_id}")
def get_questions(
    session_id: str,
    current_user=Depends(get_current_user)
):
    try:
        questions = get_questions_for_session(session_id)
        return questions
    except Exception as e:
        logger.exception(f"[questions] failed to fetch for session {session_id}: {e}")
        raise HTTPException(status_code=500, detail="failed to fetch questions")



@router.patch("/questions/{question_id}/asked")
def mark_asked(
    question_id: str,
    current_user=Depends(get_current_user)
):
    updated = mark_question_asked(question_id)
    if not updated:
        raise HTTPException(status_code=404, detail="Question not found")
    return {"status": "updated", "question_id": question_id}