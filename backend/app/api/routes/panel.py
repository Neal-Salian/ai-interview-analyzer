"""
Panel member management — add/remove panelists per session,
and trigger notification emails manually.
"""
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession
from pydantic import BaseModel, EmailStr
from typing import Optional

from app.db.database import get_db
from app.db.models import PanelMember, Session as InterviewSession
from app.api.deps import get_current_user, get_owned_session
from app.services.email import send_panel_invite, send_report_ready

router = APIRouter()
logger = logging.getLogger(__name__)


class PanelMemberCreate(BaseModel):
    name: str
    email: EmailStr
    role: Optional[str] = None
    notify_invite: bool = True
    notify_report: bool = True


@router.get("/sessions/{session_id}/panel")
def list_panel(
    session: InterviewSession = Depends(get_owned_session),
    db: DBSession = Depends(get_db),
):
    return [
        {
            "id": str(m.id),
            "name": m.name,
            "email": m.email,
            "role": m.role,
            "notify_invite": m.notify_invite,
            "notify_report": m.notify_report,
        }
        for m in session.panel_members
    ]


@router.post("/sessions/{session_id}/panel")
async def add_panel_member(
    payload: PanelMemberCreate,
    session: InterviewSession = Depends(get_owned_session),
    db: DBSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    member = PanelMember(
        id=uuid.uuid4(),
        session_id=session.id,
        name=payload.name,
        email=payload.email,
        role=payload.role,
        notify_invite=payload.notify_invite,
        notify_report=payload.notify_report,
    )
    db.add(member)
    db.commit()
    db.refresh(member)

    # Send invite immediately if requested
    if payload.notify_invite and session.scheduled_at:
        job_title = session.job.title if session.job else None
        candidate_name = session.candidate.name if session.candidate else "Candidate"
        await send_panel_invite(
            to_email=member.email,
            panel_name=member.name,
            panel_role=member.role,
            candidate_name=candidate_name,
            job_title=job_title,
            scheduled_at=session.scheduled_at.strftime("%A %d %B %Y, %H:%M"),
        )
        logger.info("[panel] invite sent to %s", member.email)

    return {"id": str(member.id), "email": member.email, "role": member.role}


@router.delete("/sessions/{session_id}/panel/{member_id}")
def remove_panel_member(
    member_id: str,
    session: InterviewSession = Depends(get_owned_session),
    db: DBSession = Depends(get_db),
):
    member = db.query(PanelMember).filter(
        PanelMember.id == member_id,
        PanelMember.session_id == session.id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Panel member not found")
    db.delete(member)
    db.commit()
    return {"deleted": member_id}


@router.post("/sessions/{session_id}/panel/notify-report")
async def notify_panel_report_ready(
    session: InterviewSession = Depends(get_owned_session),
    current_user=Depends(get_current_user),
):
    """Manually trigger report-ready emails to all panel members who opted in."""
    candidate_name = session.candidate.name if session.candidate else "Candidate"
    job_title = session.job.title if session.job else None

    sent_to = []
    for member in session.panel_members:
        if member.notify_report:
            await send_report_ready(
                to_email=member.email,
                recipient_name=member.name,
                candidate_name=candidate_name,
                job_title=job_title,
                session_id=str(session.id),
            )
            sent_to.append(member.email)

    # Also notify the recruiter
    await send_report_ready(
        to_email=current_user.email,
        recipient_name=current_user.full_name or "Recruiter",
        candidate_name=candidate_name,
        job_title=job_title,
        session_id=str(session.id),
    )
    sent_to.append(current_user.email)

    return {"notified": sent_to}