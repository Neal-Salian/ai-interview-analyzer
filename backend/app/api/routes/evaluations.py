import logging
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional

from app.db.crud import save_evaluation_feedback

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

class FeedbackRequest(BaseModel):
    session_id: str
    recruiter_id: Optional[str] = None
    evaluation_category: str
    decision: str  # 'Agree' or 'Disagree'
    correction_notes: Optional[str] = None


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """
    Recruiter feedback loop for evaluations.
    Allows recruiters to Agree/Disagree with AI evaluations to drive adaptive weighting.
    """
    if req.decision not in ["Agree", "Disagree"]:
        raise HTTPException(status_code=400, detail="Decision must be 'Agree' or 'Disagree'")
        
    try:
        save_evaluation_feedback(
            session_id=req.session_id,
            recruiter_id=req.recruiter_id,
            evaluation_category=req.evaluation_category,
            decision=req.decision,
            correction_notes=req.correction_notes
        )
        return {"status": "success", "message": "Feedback recorded successfully."}
    except Exception as e:
        logger.exception(f"[evaluations] failed to save feedback: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")
