import hmac
import hashlib
import asyncio
import uuid
import json
import datetime
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.registry import register_session, is_active
from app.db.database import get_db
from app.db.models import Candidate, Session as InterviewSession, Recruiter
from app.db.crud import get_session_by_meeting_id
from app.ml.stream.rtmp_consumer import consume_stream
from app.services.teardown import teardown_session

router = APIRouter()
logger = logging.getLogger(__name__)

TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


# ── Signature helpers ──────────────────────────────────────────────────────────

def _sign_token(plain_token: str) -> str:
    """Used only for Zoom's URL validation handshake."""
    return hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode("utf-8"),
        plain_token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def _verify_request_signature(
    raw_body: bytes,
    zoom_signature: str,
    zoom_timestamp: str,
) -> bool:
    """
    Verifies every incoming webhook POST using HMAC-SHA256.
    Zoom signs: f"v0:{timestamp}:{raw_body}" with the webhook secret.
    Header format: x-zm-signature: v0=<hex_digest>
    Also rejects requests older than 5 minutes (replay attack prevention).
    """
    if not zoom_signature or not zoom_timestamp:
        logger.warning("[webhook] Missing signature or timestamp headers")
        return False

    # Reject stale requests
    try:
        age = abs(time.time() - int(zoom_timestamp))
    except (ValueError, TypeError):
        logger.warning("[webhook] Invalid x-zm-request-timestamp value")
        return False

    if age > TIMESTAMP_TOLERANCE_SECONDS:
        logger.warning(f"[webhook] Rejected stale request (age={age:.0f}s)")
        return False

    # Recompute expected signature
    message = f"v0:{zoom_timestamp}:{raw_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison prevents timing attacks
    if not hmac.compare_digest(expected, zoom_signature):
        logger.warning("[webhook] Signature mismatch — possible spoofed request")
        return False

    return True


# ── Consumer retry wrapper ─────────────────────────────────────────────────────

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


# ── Webhook endpoint ───────────────────────────────────────────────────────────

@router.post("/zoom")
async def zoom_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    # Read raw body first — required for HMAC and manual JSON parse
    raw_body = await request.body()

    # Parse payload
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    event = payload.get("event", "")

    # ── URL validation handshake (no signature required by Zoom) ──────────────
    if event == "endpoint.url_validation":
        plain_token = payload.get("payload", {}).get("plainToken", "")
        if not plain_token:
            raise HTTPException(status_code=400, detail="Missing plainToken")
        return JSONResponse(status_code=200, content={
            "plainToken": plain_token,
            "encryptedToken": _sign_token(plain_token),
        })

    # ── Verify signature on all other events ──────────────────────────────────
    if not _verify_request_signature(
        raw_body=raw_body,
        zoom_signature=request.headers.get("x-zm-signature", ""),
        zoom_timestamp=request.headers.get("x-zm-request-timestamp", ""),
    ):
        raise HTTPException(status_code=401, detail="Invalid Zoom signature")

    event_payload = payload.get("payload", {})
    meeting_data = event_payload.get("object", {})

    # ── meeting.started ───────────────────────────────────────────────────────
    if event == "meeting.started":
        meeting_id = str(meeting_data.get("id", ""))
        topic = meeting_data.get("topic", "Unknown")
        host_email = meeting_data.get("host_email", "")

        # ── SAFETY: Do NOT create Candidate records from Zoom host data. ──
        # The host_email in a Zoom webhook payload is the *recruiter's* email,
        # not the candidate's.  Auto-creating a Candidate with this email
        # pollutes the candidates table with recruiter identities, creates
        # orphan records, and breaks downstream analytics.  Candidate records
        # must only be created through the scheduling flow where the recruiter
        # explicitly provides candidate information.

        # 1. Check for a pre-existing session (created during scheduling).
        #    This is the expected happy-path: the recruiter scheduled the
        #    interview through the UI, which created a Session row with the
        #    correct candidate_id, recruiter_id, and zoom_meeting_id.
        existing = get_session_by_meeting_id(meeting_id)

        if existing and is_active(str(existing.id)):
            logger.warning(
                f"[webhook] duplicate meeting.started for {meeting_id}, ignoring"
            )
            return JSONResponse(status_code=200, content={"message": "Already active"})

        if existing:
            # Pre-existing session found — activate it and launch the consumer.
            existing.status = "active"
            existing.started_at = datetime.datetime.utcnow()
            db.commit()
            session = existing
        else:
            # 2. No pre-scheduled session exists for this meeting.
            #    Create a session with candidate_id=None so the meeting is
            #    still recorded.  The recruiter can link a candidate later.
            #    We intentionally do NOT create a Candidate from host_email.
            logger.warning(
                f"[webhook] meeting.started — no pre-existing session for "
                f"meeting {meeting_id} (topic={topic!r}).  Creating session "
                f"without candidate.  A recruiter can link one later."
            )

            recruiter = db.query(Recruiter).filter(
                Recruiter.email == host_email
            ).first()

            session = InterviewSession(
                id=uuid.uuid4(),
                candidate_id=None,  # No candidate — see safety note above
                recruiter_id=recruiter.id if recruiter else None,
                zoom_meeting_id=meeting_id,
                status="active",
                started_at=datetime.datetime.utcnow(),
            )
            db.add(session)
            db.commit()

        session_id = str(session.id)
        rtmp_url = f"rtmp://localhost:1935/stream/{meeting_id}"

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
            "session_id": session_id,
        })

    # ── meeting.ended ─────────────────────────────────────────────────────────
    if event == "meeting.ended":
        meeting_id = str(meeting_data.get("id", ""))
        logger.info(f"[webhook] meeting.ended received for meeting {meeting_id}")

        session = get_session_by_meeting_id(meeting_id)
        if not session:
            logger.warning(
                f"[webhook] meeting.ended — no session found for {meeting_id}"
            )
            return JSONResponse(status_code=200, content={"message": "Session not found"})

        if session.status == "completed":
            logger.warning(
                f"[webhook] meeting.ended — session {session.id} already completed"
            )
            return JSONResponse(status_code=200, content={"message": "Already completed"})

        await teardown_session(session_id=str(session.id), db=db)

        logger.info(f"[webhook] session {session.id} torn down successfully")
        return JSONResponse(status_code=200, content={
            "message": "Session torn down",
            "session_id": str(session.id),
        })

    # ── All other events ──────────────────────────────────────────────────────
    logger.debug(f"[webhook] unhandled event: {event}")
    return JSONResponse(status_code=200, content={"message": "Event ignored"})