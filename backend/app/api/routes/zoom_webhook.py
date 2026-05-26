import hmac
import hashlib
import asyncio
import uuid
import datetime

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.database import get_db
from app.db.models import Candidate, Session as InterviewSession
from app.ml.stream.rtmp_consumer import consume_stream

router = APIRouter()


class ZoomPayload(BaseModel):
    plainToken: str | None = None
    object: Dict[str, Any] | None = None


class ZoomWebhookRequest(BaseModel):
    event: str
    event_ts: int
    payload: ZoomPayload


def generate_handshake_token(plain_token: str) -> str:
    msg = plain_token.encode("utf-8")
    secret = settings.ZOOM_WEBHOOK_SECRET.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


async def run_consumer_with_retry(session_id: str, rtmp_url: str):
    """
    Wraps consume_stream in a retry loop.
    If the consumer crashes (network blip, DeepFace error, etc.)
    it automatically retries up to 3 times before giving up.
    This means a brief stream interruption won't kill the pipeline.
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            print(f"[CONSUMER] Attempt {attempt}/{max_retries} "
                  f"for session {session_id}")
            await consume_stream(session_id, rtmp_url)
            print(f"[CONSUMER] Stream ended cleanly for session {session_id}")
            break
        except Exception as e:
            print(f"[CONSUMER] Attempt {attempt} failed: {e}")
            if attempt < max_retries:
                print(f"[CONSUMER] Retrying in 3 seconds...")
                await asyncio.sleep(3)
            else:
                print(f"[CONSUMER] All {max_retries} attempts exhausted "
                      f"for session {session_id}")


@router.post("/zoom")
async def zoom_webhook(
    request: ZoomWebhookRequest,
    db: Session = Depends(get_db)
):
    # Endpoint validation handshake
    if request.event == "endpoint.url_validation":
        if not request.payload.plainToken:
            raise HTTPException(status_code=400, detail="Missing plainToken")
        encrypted_token = generate_handshake_token(request.payload.plainToken)
        return JSONResponse(status_code=200, content={
            "plainToken": request.payload.plainToken,
            "encryptedToken": encrypted_token
        })

    # Meeting started — create DB records and kick off the consumer
    if request.event == "meeting.started":
        meeting_data = request.payload.object or {}
        meeting_id = str(meeting_data.get("id", ""))
        topic = meeting_data.get("topic", "Unknown")
        host_email = meeting_data.get(
            "host_email", f"host_{meeting_id}@unknown.com"
        )

        candidate = db.query(Candidate)\
            .filter(Candidate.email == host_email).first()
        if not candidate:
            candidate = Candidate(
                id=uuid.uuid4(),
                name=topic,
                email=host_email,
                created_at=datetime.datetime.utcnow()
            )
            db.add(candidate)
            db.flush()

        session = InterviewSession(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            zoom_meeting_id=meeting_id,
            status="active",
            started_at=datetime.datetime.utcnow()
        )
        db.add(session)
        db.commit()

        # Start the stream consumer in the background with auto-retry
        rtmp_url = f"rtmp://localhost:1935/live/{meeting_id}"
        asyncio.create_task(
            run_consumer_with_retry(str(session.id), rtmp_url)
        )

        print(f"[WEBHOOK] Session {session.id} started, consumer launched")
        return JSONResponse(status_code=200, content={
            "message": "Session started",
            "session_id": str(session.id)
        })

    return JSONResponse(status_code=200, content={"message": "Event ignored"})