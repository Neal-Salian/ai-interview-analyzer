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


class PanelMemberUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    notify_invite: Optional[bool] = None
    notify_report: Optional[bool] = None


def _member_response(m: PanelMember) -> dict:
    return {
        "id": str(m.id),
        "name": m.name,
        "email": m.email,
        "role": m.role,
        "notify_invite": m.notify_invite,
        "notify_report": m.notify_report,
        "created_at": m.created_at.isoformat() if m.created_at else None,
    }


@router.get("/sessions/{session_id}/panel")
def list_panel(
    session: InterviewSession = Depends(get_owned_session),
):
    return [_member_response(m) for m in session.panel_members]


@router.post("/sessions/{session_id}/panel", status_code=201)
async def add_panel_member(
    payload: PanelMemberCreate,
    session: InterviewSession = Depends(get_owned_session),
    db: DBSession = Depends(get_db),
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

    if payload.notify_invite and session.scheduled_at:
        await send_panel_invite(
            to_email=member.email,
            panel_name=member.name,
            panel_role=member.role,
            candidate_name=session.candidate.name if session.candidate else "Candidate",
            job_title=session.job.title if session.job else None,
            scheduled_at=session.scheduled_at.strftime("%A %d %B %Y, %H:%M"),
        )
        logger.info("[panel] invite sent to %s", member.email)

    return _member_response(member)


@router.patch("/sessions/{session_id}/panel/{member_id}")
def update_panel_member(
    member_id: str,
    payload: PanelMemberUpdate,
    session: InterviewSession = Depends(get_owned_session),
    db: DBSession = Depends(get_db),
):
    member = db.query(PanelMember).filter(
        PanelMember.id == member_id,
        PanelMember.session_id == session.id,
    ).first()
    if not member:
        raise HTTPException(status_code=404, detail="Panel member not found")

    if payload.name is not None:
        member.name = payload.name
    if payload.role is not None:
        member.role = payload.role
    if payload.notify_invite is not None:
        member.notify_invite = payload.notify_invite
    if payload.notify_report is not None:
        member.notify_report = payload.notify_report

    db.commit()
    db.refresh(member)
    return _member_response(member)


@router.delete("/sessions/{session_id}/panel/{member_id}", status_code=204)
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


@router.post("/sessions/{session_id}/panel/notify-report")
async def notify_panel_report_ready(
    session: InterviewSession = Depends(get_owned_session),
    current_user=Depends(get_current_user),
):
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

    await send_report_ready(
        to_email=current_user.email,
        recipient_name=current_user.full_name or "Recruiter",
        candidate_name=candidate_name,
        job_title=job_title,
        session_id=str(session.id),
    )
    sent_to.append(current_user.email)
    return {"notified": sent_to}