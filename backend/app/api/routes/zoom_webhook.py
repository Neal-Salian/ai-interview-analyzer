import hmac
import hashlib
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict

import uuid
import datetime
from app.db.models import Candidate, Session as InterviewSession

from app.core.config import settings
from app.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
class ZoomPayload(BaseModel):
    plainToken: str | None = None  
    object: Dict[str, Any] | None = None 

class ZoomWebhookRequest(BaseModel):
    event: str
    event_ts: int
    payload: ZoomPayload

def verify_zoom_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    message = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

def generate_handshake_token(plain_token: str) -> str:
    """Hashes the Zoom token specifically for the initial setup handshake"""
    msg = plain_token.encode("utf-8")
    secret = settings.ZOOM_WEBHOOK_SECRET.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


@router.post("/zoom")
async def zoom_webhook(
    request: ZoomWebhookRequest, 
    db: Session = Depends(get_db)
):
    # 1. Endpoint Validation (The Security Handshake)
    if request.event == "endpoint.url_validation":
        if not request.payload.plainToken:
            raise HTTPException(status_code=400, detail="Missing plainToken")
            
            
        encrypted_token = generate_handshake_token(request.payload.plainToken)
        
        return JSONResponse(
            status_code=200,
            content={
                "plainToken": request.payload.plainToken,
                "encryptedToken": encrypted_token
            }
        )

    # 2. Process Actual Meeting Events
    if request.event == "meeting.started":
        meeting_data = request.payload.object or {}
        meeting_id = str(meeting_data.get("id", ""))
        topic = meeting_data.get("topic", "Unknown")
        host_email = meeting_data.get("host_email", f"host_{meeting_id}@unknown.com")

        # Find or create candidate by host email
        candidate = db.query(Candidate).filter(Candidate.email == host_email).first()
        if not candidate:
            candidate = Candidate(
                id=uuid.uuid4(),
                name=topic,          # use meeting topic as stand-in name
                email=host_email,
                created_at=datetime.datetime.utcnow()
            )
            db.add(candidate)
            db.flush()               # get candidate.id before committing

        # Create a new session for this meeting
        session = InterviewSession(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            zoom_meeting_id=meeting_id,
            status="active",
            started_at=datetime.datetime.utcnow()
        )
        db.add(session)
        db.commit()

        print(f"Session created for meeting '{topic}' (ID: {meeting_id}), session: {session.id}")
        return JSONResponse(status_code=200, content={
            "message": "Session started",
            "session_id": str(session.id)
        })