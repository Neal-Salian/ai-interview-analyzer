import asyncio
import logging
import time
from contextlib import asynccontextmanager

import httpx
import sys
import threading
import traceback

def watchdog_thread(loop):
    import time
    while True:
        time.sleep(1.0)
        # Check if the loop is responsive
        start = time.time()
        future = asyncio.run_coroutine_threadsafe(asyncio.sleep(0), loop)
        try:
            future.result(timeout=4.0)
        except Exception:
            # Event loop is blocked!
            with open("deadlock_dump.txt", "w") as f:
                f.write("="*80 + "\nDEADLOCK DETECTED!\n" + "="*80 + "\n")
                for thread_id, frame in sys._current_frames().items():
                    thread_name = "Unknown"
                    for t in threading.enumerate():
                        if t.ident == thread_id:
                            thread_name = t.name
                            break
                    f.write(f"\n--- Thread: {thread_name} ({thread_id}) ---\n")
                    traceback.print_stack(frame, file=f)
            print("DEADLOCK DUMPED TO deadlock_dump.txt")
            import os
            os._exit(1)

logger = logging.getLogger(__name__)

# Captured at startup for uptime reporting in /health
_app_start_time: float = 0.0
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.deps import get_current_user, verify_development_env
from app.api.routes import zoom_webhook, zoom_oauth, jobs, sessions, questions, auth, candidates, analysis, reports, panel, evaluations, history
from app.api.websocket import connect_recruiter, disconnect_recruiter
from app.db.crud import get_active_sessions, get_session_history, get_questions_for_session
from app.ml.stream.rtmp_consumer import consume_stream

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _app_start_time
    _app_start_time = time.time()
    
    # Start the watchdog
    loop = asyncio.get_running_loop()
    threading.Thread(target=watchdog_thread, args=(loop,), daemon=True, name="WatchdogThread").start()

    # ── Structured logging setup ──────────────────────────────────────────
    from app.core.logging_config import setup_logging
    setup_logging()

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

    # ── Critical: Config Validation ───────────────────────────────────────
    from app.core.config import settings
    if not settings.ZOOM_TOKEN_ENCRYPTION_KEY:
        logger.critical("[STARTUP] ZOOM_TOKEN_ENCRYPTION_KEY is missing from environment. Aborting.")
        raise ValueError("Missing ZOOM_TOKEN_ENCRYPTION_KEY")
    if len(settings.ZOOM_TOKEN_ENCRYPTION_KEY) < 32:
        logger.warning("[STARTUP] ZOOM_TOKEN_ENCRYPTION_KEY seems invalid or too short. Fernet requires 32 url-safe base64-encoded bytes.")

    # ── Critical: Metric plugins must load ────────────────────────────────
    try:
        from app.ml.analysis.registry import discover_metrics
        discover_metrics()
        logger.info("[STARTUP] Metric plugins discovered")
    except Exception as e:
        logger.critical(f"[STARTUP] Metric discovery failed — aborting: {e}")
        raise

    # ── Critical: Preload ML libraries synchronously ────────────────────────
    # We must preload heavy ML libraries sequentially on the main thread BEFORE 
    # the server starts accepting connections. This prevents macOS GCD deadlocks 
    # and Python import lock races if a request tries to import them concurrently.
    from app.core.logging_config import log_event
    logger.info("[STARTUP] Starting synchronous ML model preload...")
    
    try:
        # Pre-import PyAV to avoid AVFoundation deadlocks when spawned in tasks
        import av
        logger.info("[STARTUP] PyAV imported successfully.")
    except Exception as e:
        logger.warning(f"[STARTUP] PyAV import failed: {e}")
        
    try:
        from app.ml.speech.transcriber import _get_model as preload_whisper
        preload_whisper()
        logger.info("[STARTUP] Whisper model preloaded successfully.")
    except Exception as e:
        logger.warning(f"[STARTUP] Whisper preload failed (will retry on demand): {e}")

    try:
        from app.ml.tracking.candidate_tracker import _ensure_deepface_model
        _ensure_deepface_model()
        logger.info("[STARTUP] DeepFace model preloaded successfully.")
    except Exception as e:
        logger.warning(f"[STARTUP] DeepFace preload failed: {e}")

    # ── Non-critical: Recover active streaming sessions ───────────────────
    try:
        active = get_active_sessions()
        
        async def recovery_task(sessions):
            from app.core.config import settings
            from app.services.ai.rtmp_service import start as start_rtmp
            from app.core.logging_config import log_event
            
            logger.info(f"[RECOVERY] Started background recovery for {len(sessions)} session(s).")
            log_event(logger, "recovery_started", session_count=len(sessions))
            
            # Limit concurrent recoveries to avoid executor starvation
            semaphore = asyncio.Semaphore(2)
            
            async def recover_single(session):
                async with semaphore:
                    if session.zoom_meeting_id:
                        rtmp_url = f"{settings.RTMP_SERVER_URL}/stream/{session.zoom_meeting_id}"
                        logger.info(f"[RECOVERY] Attempting recovery for session {session.id}")
                        try:
                            result = await start_rtmp(str(session.id), rtmp_url)
                            if not result.get("success"):
                                logger.warning(f"[RECOVERY] Orphan or failed session {session.id}: {result.get('error')}")
                                log_event(logger, "recovery_failed", session_id=str(session.id), error=result.get("error"))
                            else:
                                logger.info(f"[RECOVERY] Successfully recovered session {session.id}")
                        except Exception as e:
                            logger.error(f"[RECOVERY] Unexpected error for session {session.id}: {e}")
            
            await asyncio.gather(*(recover_single(s) for s in sessions))
            
            logger.info("[RECOVERY] Finished all background recovery tasks.")
            log_event(logger, "recovery_finished")

        if active:
            asyncio.create_task(recovery_task(active))
        else:
            logger.info("[STARTUP] No active sessions found. Skipping recovery.")
            from app.core.logging_config import log_event
            log_event(logger, "recovery_skipped")
            
    except Exception as e:
        logger.warning(f"[STARTUP] Could not initiate active session recovery: {e}")

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
app.include_router(zoom_oauth.router, prefix="/api")
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
async def health():
    """
    Comprehensive health check — probes Database, Ollama, and RTMP subsystems.

    Always returns HTTP 200 (so Docker/k8s healthchecks pass even when
    degraded).  The JSON body distinguishes "healthy" vs "degraded".
    """
    from app.core.registry import _registry

    db_ok = _check_database()
    ollama_ok = await _check_ollama()
    rtmp_ok = await _check_rtmp()

    all_healthy = db_ok and ollama_ok and rtmp_ok

    return {
        "status": "healthy" if all_healthy else "degraded",
        "database": db_ok,
        "ollama": ollama_ok,
        "rtmp": rtmp_ok,
        "active_sessions": len(_registry),
        "uptime_seconds": round(time.monotonic() - _app_start_time, 1),
    }


def _check_database() -> bool:
    """Probe database with SELECT 1."""
    try:
        from app.db.database import engine
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"[health] database check failed: {e}")
        return False


async def _check_ollama() -> bool:
    """Probe Ollama API and verify the configured model exists."""
    try:
        from app.core.config import settings
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(f"{settings.OLLAMA_BASE_URL.rstrip('/')}/api/tags")
            if resp.status_code != 200:
                return False
            data = resp.json()
            models = [m.get("name") for m in data.get("models", [])]
            return settings.OLLAMA_MODEL in models
    except Exception:
        return False


async def _check_rtmp() -> bool:
    """Probe nginx-rtmp stats page."""
    try:
        from app.core.config import settings
        async with httpx.AsyncClient(timeout=3.0) as client:
            resp = await client.get(settings.RTMP_STAT_URL)
            return resp.status_code == 200
    except Exception:
        return False


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
    connected = await connect_recruiter(session_id, websocket)
    if not connected:
        return
        
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
                raw = await asyncio.wait_for(websocket.receive_text(), timeout=30.0)

                # ── Parse incoming WebSocket commands ─────────────────
                try:
                    import json
                    msg = json.loads(raw)
                    msg_type = msg.get("type", "")

                    if msg_type == "enroll_candidate":
                        await _handle_enroll_candidate(session_id, websocket)

                except (json.JSONDecodeError, TypeError):
                    pass  # Plain text keepalive — ignore

            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        disconnect_recruiter(session_id, websocket)
    except Exception as e:
        logger.exception(f"[WS] Unexpected error for {session_id}: {e}")
        disconnect_recruiter(session_id, websocket)



# ── Candidate Enrollment Handler ─────────────────────────────────────────

async def _handle_enroll_candidate(session_id: str, websocket: WebSocket):
    """
    Handle the 'enroll_candidate' WebSocket command.

    Transitions tracking state to ENROLLING. The RTMP consumer detects
    this state change and begins capturing enrollment frames. This handler
    polls for completion or timeout.
    """
    from app.runtime.manager import RuntimeManager
    from app.ml.tracking.candidate_tracker import TrackingStatus
    from app.core.config import settings
    from app.core.logging_config import log_event

    current_status = RuntimeManager.get_tracking_status(session_id)

    if current_status not in (TrackingStatus.NOT_ENROLLED, TrackingStatus.LOST):
        await websocket.send_json({
            "type": "enrollment_status",
            "status": "rejected",
            "reason": f"Cannot enroll from state: {current_status}",
        })
        return

    # Signal the RTMP consumer to start capturing enrollment frames
    RuntimeManager.update_tracking_metadata(
        session_id,
        tracking_status=TrackingStatus.ENROLLING,
        enrollment_start_time=time.time(),
        enrollment_error=None,
    )

    log_event(logger, "enrollment_started", session_id=session_id)

    await websocket.send_json({
        "type": "enrollment_status",
        "status": "enrolling",
        "message": "Candidate enrollment started. Ask candidate to look at camera.",
    })

    # Poll for completion or timeout — the RTMP consumer performs the actual enrollment
    timeout = settings.ENROLLMENT_TIMEOUT_SECONDS
    poll_interval = 0.5
    elapsed = 0.0

    while elapsed < timeout:
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval

        status = RuntimeManager.get_tracking_status(session_id)

        if status == TrackingStatus.TRACKING:
            meta = RuntimeManager.get_tracking_metadata(session_id)
            log_event(logger, "enrollment_completed", session_id=session_id)
            await websocket.send_json({
                "type": "enrollment_status",
                "status": "enrolled",
                "confidence": meta.get("confidence", 0.0) if meta else 0.0,
            })
            return

        if status != TrackingStatus.ENROLLING:
            meta = RuntimeManager.get_tracking_metadata(session_id)
            error_reason = meta.get("enrollment_error") if meta else None
            
            if status == TrackingStatus.NOT_ENROLLED and error_reason:
                await websocket.send_json({
                    "type": "enrollment_status",
                    "status": "failed",
                    "reason": error_reason,
                })
            else:
                # Something else transitioned the state (e.g. session ended)
                await websocket.send_json({
                    "type": "enrollment_status",
                    "status": "failed",
                    "reason": f"Enrollment interrupted — state became: {status}",
                })
            return

    # Timeout — revert to NOT_ENROLLED
    RuntimeManager.update_tracking_metadata(
        session_id,
        tracking_status=TrackingStatus.NOT_ENROLLED,
        enrollment_start_time=None,
    )
    log_event(logger, "enrollment_timeout", session_id=session_id,
              timeout_seconds=timeout)

    await websocket.send_json({
        "type": "enrollment_status",
        "status": "timeout",
        "reason": f"Enrollment timed out after {timeout}s. Please retry.",
    })


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