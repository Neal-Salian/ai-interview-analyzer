import asyncio
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user, verify_development_env
from app.api.routes import zoom_webhook, jobs, sessions, questions, auth, candidates, analysis, reports, panel, evaluations, history
from app.api.websocket import connect_recruiter, disconnect_recruiter
from app.db.crud import get_active_sessions, get_session_history, get_questions_for_session
from app.ml.stream.rtmp_consumer import consume_stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Critical: Database must be reachable ──────────────────────────────
    from app.db.database import engine
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("[STARTUP] Database connection verified")
    except Exception as e:
        logger.critical(f"[STARTUP] Database unavailable — aborting: {e}")
        raise

    # ── Critical: Metric plugins must load ────────────────────────────────
    try:
        from app.ml.analysis.registry import discover_metrics
        discover_metrics()
        logger.info("[STARTUP] Metric plugins discovered")
    except Exception as e:
        logger.critical(f"[STARTUP] Metric discovery failed — aborting: {e}")
        raise

    # ── Non-critical: Recover active streaming sessions ───────────────────
    try:
        active = get_active_sessions()
        for session in active:
            if session.zoom_meeting_id:
                rtmp_url = f"rtmp://localhost:1935/stream/{session.zoom_meeting_id}"
                logger.info(f"[STARTUP] Recovering consumer for session {session.id}")
                asyncio.create_task(consume_stream(str(session.id), rtmp_url))
        logger.info(f"[STARTUP] Recovery check done — {len(active)} active session(s) found")
    except Exception as e:
        logger.warning(f"[STARTUP] Could not recover active sessions: {e}")

    yield


app = FastAPI(title="AI Interview Analyzer", lifespan=lifespan)

from app.core.rate_limit import limiter, RateLimitExceeded, _rate_limit_exceeded_handler
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

from app.core.config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,  # Important for cookies
)

app.include_router(zoom_webhook.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")
app.include_router(questions.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(candidates.router, prefix="/api")
app.include_router(analysis.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(panel.router, prefix="/api")
app.include_router(evaluations.router, prefix="/api")
app.include_router(history.router, prefix="/api")

from app.api.routes import admin
app.include_router(admin.router, prefix="/api")

# Ensure uploads directory exists (used by resume upload endpoint)
import os
os.makedirs("uploads", exist_ok=True)
# NOTE: StaticFiles mount for /api/uploads was removed for security.
# Resumes are now served via authenticated GET /api/candidates/{id}/resume.


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/live/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, 
    session_id: str,
    token: str = Query(None),
    db: Session = Depends(get_db)
):
    await websocket.accept()

    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    try:
        get_current_user(token=token, db=db)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # Note: connect_recruiter no longer calls accept() since we accepted above
    await connect_recruiter(session_id, websocket)
    try:
        try:
            history = await asyncio.to_thread(get_session_history, session_id)
            questions_history = await asyncio.to_thread(get_questions_for_session, session_id)
            if history["emotions"] or history["transcripts"] or questions_history:
                await websocket.send_json({
                    "type": "history",
                    "emotions": history["emotions"],
                    "transcripts": history["transcripts"],
                    "questions": questions_history
                })
                logger.info(f"[WS] Replayed {len(history['emotions'])} emotions, "
                            f"{len(history['transcripts'])} transcripts to session {session_id}")
        except Exception as e:
            logger.exception(f"[WS] History fetch failed for {session_id}: {e}")
            # Don't close — keep connection open for live updates

        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        disconnect_recruiter(session_id)
    except Exception as e:
        logger.exception(f"[WS] Unexpected error for {session_id}: {e}")
        disconnect_recruiter(session_id)



# Internal test endpoint — broadcasts a fake emotion to a session
# Only used for testing WebSocket broadcast, remove before production
@app.post(
    "/internal/test-broadcast/{session_id}",
    dependencies=[Depends(verify_development_env)]
)
async def test_broadcast(session_id: str):
    from app.api.websocket import broadcast
    await broadcast(session_id, {
        "type": "emotion",
        "dominant_emotion": "surprised",
        "confidence": 91.2
    })
    return {"status": "broadcast sent"}