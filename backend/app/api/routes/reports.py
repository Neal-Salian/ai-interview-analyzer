"""
Report routes — JSON and PDF report endpoints.

GET  /reports/{session_id}      → structured 11-section report JSON
GET  /reports/{session_id}/pdf  → downloadable PDF report
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.api.deps import get_current_user, get_owned_session
from app.db.models import Session as InterviewSession

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/reports/{session_id}")
def get_report(
    session: InterviewSession = Depends(get_owned_session),
    db: Session = Depends(get_db),
):
    from app.ml.report.generator import generate_report
    report = generate_report(str(session.id), db)
    if report.get("error"):
        raise HTTPException(status_code=404, detail=report["error"])
    return report


@router.get("/reports/{session_id}/pdf")
def download_report_pdf(
    session: InterviewSession = Depends(get_owned_session),
    db: Session = Depends(get_db),
):
    from app.ml.report.generator import generate_report
    from app.ml.report.pdf_builder import build_pdf

    report = generate_report(str(session.id), db)
    if report.get("error"):
        raise HTTPException(status_code=404, detail=report["error"])

    try:
        pdf_bytes = build_pdf(report)
    except Exception as e:
        logger.exception(f"[REPORT] PDF generation failed: {e}")
        raise HTTPException(status_code=500, detail="PDF generation failed")

    candidate = report.get("executive_summary", {}).get("candidate", "candidate")
    filename = f"interview_report_{candidate}_{str(session.id)[:8]}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )