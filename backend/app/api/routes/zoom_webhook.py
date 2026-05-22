import hashlib
import hmac
import json
from fastapi import APIRouter, Request, HTTPException, Depends
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.db.models import Candidate, Session as InterviewSession
from app.core.config import settings

router = APIRouter()

def verify_zoom_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    message = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

@router.post("/webhook/zoom")
async def zoom_webhook(request: Request, db: Session = Depends(get_db)):
    body = await request.body()
    timestamp = request.headers.get("x-zm-request-timestamp", "")
    signature = request.headers.get("x-zm-signature", "")

    # Zoom URL validation challenge (one-time handshake)
    payload = json.loads(body)
    if payload.get("event") == "endpoint.url_validation":
        plain_token = payload["payload"]["plainToken"]
        hashed = hmac.new(
            settings.ZOOM_WEBHOOK_SECRET.encode(),
            plain_token.encode(),
            hashlib.sha256
        ).hexdigest()
        return {
            "plainToken": plain_token,
            "encryptedToken": hashed
        }

    # Verify signature on all other events
    if not verify_zoom_signature(body, timestamp, signature):
        raise HTTPException(status_code=401, detail="Invalid Zoom signature")

    event = payload.get("event")

    if event == "meeting.started":
        meeting_payload = payload.get("payload", {}).get("object", {})
        zoom_meeting_id = str(meeting_payload.get("id"))
        host_email = meeting_payload.get("host_email", "unknown@zoom.us")
        host_name = meeting_payload.get("topic", "Unknown Candidate")

        # Get or create candidate by email
        candidate = db.query(Candidate).filter(
            Candidate.email == host_email
        ).first()

        if not candidate:
            candidate = Candidate(
                name=host_name,
                email=host_email
            )
            db.add(candidate)
            db.flush()  # get candidate.id without full commit

        # Create new interview session
        session = InterviewSession(
            candidate_id=candidate.id,
            status="active",
            zoom_meeting_id=zoom_meeting_id  # add this column if not present
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        print(f"[ZOOM] Session {session.id} created for candidate {candidate.email}")
        return {"status": "session_created", "session_id": session.id}

    if event == "meeting.ended":
        zoom_meeting_id = str(
            payload.get("payload", {}).get("object", {}).get("id")
        )
        session = db.query(InterviewSession).filter(
            InterviewSession.zoom_meeting_id == zoom_meeting_id,
            InterviewSession.status == "active"
        ).first()

        if session:
            session.status = "completed"
            db.commit()
            print(f"[ZOOM] Session {session.id} marked completed")

    return {"status": "ok"}