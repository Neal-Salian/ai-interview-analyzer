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
from app.db.database import get_db, SessionLocal
from app.db.models import Candidate, Session as InterviewSession, Recruiter
from app.db.crud import get_session_by_meeting_id
from app.ml.stream.rtmp_consumer import consume_stream
from app.services.teardown import teardown_session

router = APIRouter()
logger = logging.getLogger(__name__)

TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


# ── In-memory idempotency guard ───────────────────────────────────────────────
# Zoom may deliver the same webhook event multiple times (retries on timeout,
# network issues, or edge-triggered duplicates).  This lightweight guard
# prevents processing the same (event_type, meeting_id) pair more than once
# within a short TTL window.
#
# Limitations:
#   - In-memory only: does not survive server restarts.
#   - Per-process: does not protect across multiple worker processes.
#   - NOT a substitute for database-level idempotency constraints.
#
# For this single-process asyncio server, it is sufficient to close the race
# windows between duplicate deliveries that arrive seconds apart.

_IDEMPOTENCY_TTL_SECONDS = 300  # 5-minute window matches Zoom's retry policy
_processed_events: dict[str, float] = {}  # key → timestamp of first processing


def _is_duplicate_event(event_type: str, meeting_id: str) -> bool:
    """
    Returns True if this (event_type, meeting_id) was already processed
    within the TTL window.  If not, marks it as processed and returns False.

    Also lazily prunes expired entries to prevent unbounded memory growth.
    """
    key = f"{event_type}:{meeting_id}"
    now = time.time()

    # Lazy pruning: remove expired entries on each call.
    # With typical webhook volume (tens per minute) this is cheap.
    expired = [k for k, ts in _processed_events.items() if now - ts > _IDEMPOTENCY_TTL_SECONDS]
    for k in expired:
        del _processed_events[k]

    if key in _processed_events:
        age = now - _processed_events[key]
        logger.info(
            f"[idempotency] duplicate {event_type} for meeting {meeting_id} "
            f"(first seen {age:.1f}s ago), skipping"
        )
        return True

    _processed_events[key] = now
    return False


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

        # Idempotency: reject duplicate deliveries before any DB work
        if _is_duplicate_event("meeting.started", meeting_id):
            return JSONResponse(status_code=200, content={"message": "Already processed"})

        # ── Validate meeting_id ───────────────────────────────────────────
        # A blank or missing meeting ID cannot be mapped to any session and
        # would create an unlinkable orphan.  Log and exit cleanly.
        if not meeting_id:
            logger.error(
                "[webhook] meeting.started — payload has empty/missing "
                "meeting ID.  Cannot map to session.  Skipping."
            )
            return JSONResponse(status_code=200, content={"message": "Missing meeting ID"})

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
            logger.info(
                f"[webhook] meeting.started — matched pre-existing session "
                f"{existing.id} (candidate_id={existing.candidate_id}, "
                f"recruiter_id={existing.recruiter_id})"
            )
        else:
            # 2. No pre-scheduled session exists for this meeting.
            #    This creates a PARTIALLY POPULATED session (candidate_id=None).
            #    We still record it so audio/video isn't lost, but log it
            #    prominently so ops can track orphan rates.
            #    We intentionally do NOT create a Candidate from host_email.

            if not host_email:
                logger.warning(
                    f"[webhook] meeting.started — meeting {meeting_id} has no "
                    f"host_email.  Session will have no recruiter link."
                )

            recruiter = None
            if host_email:
                recruiter = db.query(Recruiter).filter(
                    Recruiter.email == host_email
                ).first()
                if not recruiter:
                    logger.warning(
                        f"[webhook] meeting.started — host_email {host_email!r} "
                        f"does not match any registered recruiter."
                    )

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

            # ── Orphan session audit log ──────────────────────────────────
            logger.warning(
                f"[webhook] ORPHAN SESSION CREATED — "
                f"session_id={session.id}, "
                f"meeting_id={meeting_id}, "
                f"topic={topic!r}, "
                f"candidate_id=None, "
                f"recruiter_id={session.recruiter_id}, "
                f"host_email={host_email!r}.  "
                f"This session has no candidate.  A recruiter must link "
                f"one through the UI or API."
            )

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

        # Idempotency: reject duplicate deliveries before any DB/teardown work
        if _is_duplicate_event("meeting.ended", meeting_id):
            return JSONResponse(status_code=200, content={"message": "Already processed"})

        # ── Validate meeting_id ───────────────────────────────────────────
        if not meeting_id:
            logger.error(
                "[webhook] meeting.ended — payload has empty/missing "
                "meeting ID.  Cannot map to session.  Skipping."
            )
            return JSONResponse(status_code=200, content={"message": "Missing meeting ID"})

        session = get_session_by_meeting_id(meeting_id)
        if not session:
            # This can happen if: (a) meeting was never tracked by the platform,
            # (b) the session was created without a zoom_meeting_id, or
            # (c) the meeting.started webhook was missed/failed.
            logger.warning(
                f"[webhook] meeting.ended — no session found for meeting "
                f"{meeting_id}.  Possible causes: meeting not scheduled in "
                f"platform, meeting.started webhook missed, or meeting ID "
                f"mismatch.  No teardown will run."
            )
            return JSONResponse(status_code=200, content={"message": "Session not found"})

        if session.status == "completed":
            logger.warning(
                f"[webhook] meeting.ended — session {session.id} already completed"
            )
            return JSONResponse(status_code=200, content={"message": "Already completed"})

        # ── Fire-and-forget teardown ──────────────────────────────────────
        # Zoom expects a response within a few seconds or it will retry the
        # webhook.  teardown_session() cancels the RTMP consumer, runs
        # metrics aggregation, and sends email notifications — all of which
        # can take 10+ seconds.  We return 200 immediately and run teardown
        # as a background asyncio task.
        #
        # The request-scoped `db` (from Depends(get_db)) is closed once the
        # response is sent, so the background task creates its own
        # SessionLocal() and is responsible for closing it.
        sid = str(session.id)

        async def _background_teardown(session_id: str) -> None:
            bg_db = SessionLocal()
            try:
                logger.info(
                    f"[webhook] background teardown started for session {session_id}"
                )
                await teardown_session(session_id=session_id, db=bg_db)
                logger.info(
                    f"[webhook] background teardown completed for session {session_id}"
                )
            except Exception:
                logger.exception(
                    f"[webhook] background teardown FAILED for session {session_id}"
                )
            finally:
                bg_db.close()

        asyncio.create_task(_background_teardown(sid))
        logger.info(
            f"[webhook] meeting.ended — teardown task launched for "
            f"session {sid}, returning 200 to Zoom"
        )

        return JSONResponse(status_code=200, content={
            "message": "Session teardown initiated",
            "session_id": sid,
        })

    # ── All other events ──────────────────────────────────────────────────────
    logger.debug(f"[webhook] unhandled event: {event}")
    return JSONResponse(status_code=200, content={"message": "Event ignored"})