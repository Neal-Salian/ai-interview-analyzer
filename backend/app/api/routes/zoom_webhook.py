import hmac
import hashlib
import asyncio
import uuid
import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.registry import register_session, is_active
from app.db.database import get_db
from app.db.models import Candidate, Session as InterviewSession
from app.db.crud import get_session_by_meeting_id
from app.ml.stream.rtmp_consumer import consume_stream
from app.services.teardown import teardown_session

router = APIRouter()
logger = logging.getLogger(__name__)


class ZoomPayload(BaseModel):
    plainToken: str | None = None
    object: Dict[str, Any] | None = None


class ZoomWebhookRequest(BaseModel):
    event: str
    event_ts: int
    payload: ZoomPayload


def verify_zoom_signature(plain_token: str) -> str:
    msg = plain_token.encode("utf-8")
    secret = settings.ZOOM_WEBHOOK_SECRET.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


async def run_consumer_with_retry(session_id: str, rtmp_url: str):
    """
    Wraps consume_stream in a retry loop.
    Retries up to 3 times with a 3-second gap on failure.
    A brief stream blip won't kill the pipeline.
    """
    max_retries = 3
    for attempt in range(1, max_retries + 1):
        try:
            logger.info(
                f"[consumer] attempt {attempt}/{max_retries} "
                f"for session {session_id}"
            )
            await consume_stream(session_id, rtmp_url)
            logger.info(f"[consumer] stream ended cleanly for session {session_id}")
            break
        except asyncio.CancelledError:
            # Teardown cancelled this task intentionally — exit cleanly
            logger.info(f"[consumer] cancelled for session {session_id}")
            raise
        except Exception as e:
            logger.warning(f"[consumer] attempt {attempt} failed: {e}")
            if attempt < max_retries:
                logger.info("[consumer] retrying in 3 seconds...")
                await asyncio.sleep(3)
            else:
                logger.error(
                    f"[consumer] all {max_retries} attempts exhausted "
                    f"for session {session_id}"
                )


@router.post("/zoom")
async def zoom_webhook(
    request: ZoomWebhookRequest,
    db: Session = Depends(get_db)
):
    # ── Endpoint URL validation handshake ─────────────────────────────────────
    if request.event == "endpoint.url_validation":
        if not request.payload.plainToken:
            raise HTTPException(status_code=400, detail="Missing plainToken")
        encrypted_token = verify_zoom_signature(request.payload.plainToken)
        return JSONResponse(status_code=200, content={
            "plainToken": request.payload.plainToken,
            "encryptedToken": encrypted_token
        })

    # ── meeting.started ───────────────────────────────────────────────────────
    if request.event == "meeting.started":
        meeting_data = request.payload.object or {}
        meeting_id = str(meeting_data.get("id", ""))
        topic = meeting_data.get("topic", "Unknown")
        host_email = meeting_data.get(
            "host_email", f"host_{meeting_id}@unknown.com"
        )

        # Deduplicate: if consumer is already running, ignore the duplicate webhook
        existing = get_session_by_meeting_id(meeting_id)
        if existing and is_active(str(existing.id)):
            logger.warning(
                f"[webhook] duplicate meeting.started for {meeting_id}, ignoring"
            )
            return JSONResponse(status_code=200, content={"message": "Already active"})

        # Create candidate if not seen before
        candidate = db.query(Candidate).filter(
            Candidate.email == host_email
        ).first()
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

        session_id = str(session.id)
        rtmp_url = f"rtmp://localhost:1935/live/{meeting_id}"

        # Launch consumer and immediately register it in the task registry
        # so teardown_session() can cancel it by session_id
        consumer_task = asyncio.create_task(
            run_consumer_with_retry(session_id, rtmp_url)
        )
        register_session(session_id, consumer_task)

        logger.info(
            f"[webhook] meeting.started — session {session_id} "
            f"launched and registered"
        )
        return JSONResponse(status_code=200, content={
            "message": "Session started",
            "session_id": session_id
        })

    # ── meeting.ended ─────────────────────────────────────────────────────────
    if request.event == "meeting.ended":
        meeting_data = request.payload.object or {}
        meeting_id = str(meeting_data.get("id", ""))

        logger.info(f"[webhook] meeting.ended received for meeting {meeting_id}")

        session = get_session_by_meeting_id(meeting_id)
        if not session:
            logger.warning(
                f"[webhook] meeting.ended — no session found "
                f"for meeting {meeting_id}, ignoring"
            )
            return JSONResponse(status_code=200, content={"message": "Session not found"})

        if session.status == "completed":
            logger.warning(
                f"[webhook] meeting.ended — session {session.id} "
                f"already completed, ignoring duplicate"
            )
            return JSONResponse(status_code=200, content={"message": "Already completed"})

        await teardown_session(session_id=str(session.id), db=db)

        logger.info(f"[webhook] session {session.id} torn down successfully")
        return JSONResponse(status_code=200, content={
            "message": "Session torn down",
            "session_id": str(session.id)
        })

    # ── All other events ──────────────────────────────────────────────────────
    logger.debug(f"[webhook] unhandled event: {request.event}")
    return JSONResponse(status_code=200, content={"message": "Event ignored"})