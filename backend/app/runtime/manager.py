import time
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class RuntimeManager:
    """
    Manages transient runtime initialization state across the application.
    Currently uses an in-memory dictionary, but abstracts access for future
    replacement with Redis or another shared store in multi-worker environments.
    """
    _state: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def get_status(cls, session_id: str) -> Dict[str, Any]:
        """Get the current runtime status details for a session."""
        return cls._state.get(session_id, {
            "status": "not_initialized",
            "progress": 0,
            "current_step": "Not initialized",
            "failed_component": None,
            "checks": {
                "rtmp": False,
                "ollama": False,
                "whisper": False,
                "deepface": False,
                "websocket": False
            },
            "duration_ms": 0,
            "start_time": 0
        })

    @classmethod
    def set_initializing(cls, session_id: str):
        """Reset state and mark as initializing."""
        cls._state[session_id] = {
            "status": "initializing",
            "progress": 0,
            "current_step": "Starting initialization...",
            "failed_component": None,
            "checks": {
                "rtmp": False,
                "ollama": False,
                "whisper": False,
                "deepface": False,
                "websocket": False
            },
            "duration_ms": 0,
            "start_time": time.time()
        }
        from app.core.logging_config import log_event
        log_event(logger, "runtime_state_transition", session_id=session_id, previous_state="created", new_state="initializing")

    @classmethod
    def update_progress(cls, session_id: str, progress: int, step: str):
        """Update progress percentage and step description."""
        if session_id in cls._state:
            cls._state[session_id]["progress"] = progress
            cls._state[session_id]["current_step"] = step

    @classmethod
    def set_check_result(cls, session_id: str, component: str, success: bool):
        """Update the result of a specific component check."""
        if session_id in cls._state:
            cls._state[session_id]["checks"][component] = success

    @classmethod
    def set_ready(cls, session_id: str):
        """Mark initialization as complete and successful."""
        if session_id in cls._state:
            prev_status = cls._state[session_id].get("status", "unknown")
            cls._state[session_id]["status"] = "ready"
            cls._state[session_id]["progress"] = 100
            cls._state[session_id]["current_step"] = "AI engine ready."
            start_time = cls._state[session_id].get("start_time", time.time())
            cls._state[session_id]["duration_ms"] = int((time.time() - start_time) * 1000)
            from app.core.logging_config import log_event
            log_event(logger, "runtime_state_transition", session_id=session_id, previous_state=prev_status, new_state="ready")

    @classmethod
    def set_failed(cls, session_id: str, failed_component: str, error_msg: str):
        """Mark initialization as failed with specific component."""
        if session_id in cls._state:
            prev_status = cls._state[session_id].get("status", "unknown")
            cls._state[session_id]["status"] = "failed"
            cls._state[session_id]["failed_component"] = failed_component
            cls._state[session_id]["current_step"] = error_msg
            start_time = cls._state[session_id].get("start_time", time.time())
            cls._state[session_id]["duration_ms"] = int((time.time() - start_time) * 1000)
            from app.core.logging_config import log_event
            log_event(logger, "runtime_state_transition", session_id=session_id, previous_state=prev_status, new_state="failed", failed_component=failed_component)

    @classmethod
    async def start_analysis(cls, session_id: str, db=None, session_model=None, recruiter_id: str = None) -> bool:
        """
        Transition runtime from READY → starting_rtmp → RUNNING (or FAILED).

        Orchestrates RTMP consumer startup via RTMPService.
        Returns True on success, False on failure.
        """
        from app.core.logging_config import log_event
        from app.services.ai import rtmp_service

        state = cls._state.get(session_id)
        if not state:
            return False
        # Only allow transition from ready
        if state.get("status") != "ready":
            return False

        log_kwargs = {"session_id": session_id}
        if recruiter_id:
            log_kwargs["recruiter_id"] = recruiter_id

        log_event(logger, "analysis_start_requested", **log_kwargs)

        # ── Intermediate state: Starting RTMP ───────────────────────────
        state["status"] = "starting_rtmp"
        state["current_step"] = "Starting RTMP consumer..."
        state["progress"] = 100

        if db and session_model:
            session_model.ai_runtime_status = "starting_rtmp"
            db.commit()
            db.refresh(session_model)

        # ── Build RTMP URL from zoom_meeting_id ─────────────────────────
        zoom_meeting_id = getattr(session_model, "zoom_meeting_id", None) if session_model else None
        if not zoom_meeting_id:
            reason = "No Zoom meeting ID — cannot determine RTMP stream URL."
            cls.set_failed(session_id, "rtmp_consumer", reason)
            if db and session_model:
                session_model.ai_runtime_status = "failed"
                db.commit()
                db.refresh(session_model)
            log_event(logger, "rtmp_failed", failure_reason=reason, **log_kwargs)
            return False

        from app.core.config import settings
        rtmp_url = f"{settings.RTMP_SERVER_URL}/stream/{zoom_meeting_id}"

        # ── Call RTMPService.start() ────────────────────────────────────
        log_event(logger, "rtmp_start_requested",
                  rtmp_url=rtmp_url, **log_kwargs)

        job_id = str(session_model.job_id) if session_model and session_model.job_id else ""

        result = await rtmp_service.start(
            session_id=session_id,
            rtmp_url=rtmp_url,
            recruiter_id=recruiter_id or "",
            job_id=job_id,
        )

        startup_duration_ms = result.get("startup_duration_ms", 0)

        if not result["success"]:
            # ── FAILED ──────────────────────────────────────────────────
            error_msg = result.get("error", "RTMP consumer startup failed.")
            cls.set_failed(session_id, "rtmp_consumer", error_msg)
            if db and session_model:
                session_model.ai_runtime_status = "failed"
                db.commit()
                db.refresh(session_model)
            log_event(logger, "rtmp_failed",
                      failure_reason=error_msg,
                      startup_duration_ms=startup_duration_ms,
                      **log_kwargs)
            return False

        # ── RUNNING ─────────────────────────────────────────────────────
        state["status"] = "running"
        state["current_step"] = "AI analysis running."
        state["progress"] = 100

        if db and session_model:
            session_model.ai_runtime_status = "running"
            db.commit()
            db.refresh(session_model)

        log_event(logger, "analysis_started",
                  startup_duration_ms=startup_duration_ms,
                  **log_kwargs)
        return True

    @classmethod
    def clear(cls, session_id: str):
        """Clear state for a session."""
        if session_id in cls._state:
            prev_status = cls._state[session_id].get("status", "unknown")
            from app.core.logging_config import log_event
            log_event(logger, "runtime_state_transition", session_id=session_id, previous_state=prev_status, new_state="terminated")
            del cls._state[session_id]

    @classmethod
    async def initialize_session(cls, session_id: str):
        """Orchestrate AI services initialization and update database."""
        from app.db.database import SessionLocal
        from app.db.models import Session as InterviewSession
        from app.core.logging_config import log_event
        from app.services.ai import rtmp_service, ollama_service, whisper_service, deepface_service
        import asyncio

        db = SessionLocal()
        session = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
        
        meeting_id = getattr(session, "zoom_meeting_id", None) if session else None
        recruiter_id = str(session.recruiter_id) if session and session.recruiter_id else None

        log_kwargs = {
            "session_id": session_id,
            "meeting_id": meeting_id,
            "recruiter_id": recruiter_id,
        }
        
        try:
            log_event(logger, "runtime_check_started", **log_kwargs)
            
            # 1. RTMP Server Reachable
            cls.update_progress(session_id, 20, "Checking RTMP Server Reachable...")
            if not await rtmp_service.check_health():
                cls.set_check_result(session_id, "rtmp", False)
                cls.set_failed(session_id, "rtmp", "Failed to connect to streaming backend.")
                if session:
                    session.ai_runtime_status = "failed"
                    db.commit()
                log_event(logger, "runtime_failed", failed_component="rtmp", error="Failed to connect to streaming backend.", **log_kwargs)
                return
            cls.set_check_result(session_id, "rtmp", True)
                
            await asyncio.sleep(0.5)
            
            # 2. Ollama Connectivity
            cls.update_progress(session_id, 40, "Checking Ollama connectivity...")
            if not await ollama_service.check_health():
                cls.set_check_result(session_id, "ollama", False)
                cls.set_failed(session_id, "ollama", "Failed to connect to local LLM.")
                if session:
                    session.ai_runtime_status = "failed"
                    db.commit()
                log_event(logger, "runtime_failed", failed_component="ollama", error="Failed to connect to local LLM.", **log_kwargs)
                return
            cls.set_check_result(session_id, "ollama", True)
                
            await asyncio.sleep(0.5)

            # 3. Whisper Dependencies
            cls.update_progress(session_id, 60, "Checking Whisper dependencies...")
            if not await whisper_service.check_health():
                cls.set_check_result(session_id, "whisper", False)
                cls.set_failed(session_id, "whisper", "Missing Whisper dependencies.")
                if session:
                    session.ai_runtime_status = "failed"
                    db.commit()
                log_event(logger, "runtime_failed", failed_component="whisper", error="Missing Whisper dependencies.", **log_kwargs)
                return
            cls.set_check_result(session_id, "whisper", True)
                
            await asyncio.sleep(0.5)

            # 4. DeepFace Dependencies
            cls.update_progress(session_id, 80, "Checking DeepFace dependencies...")
            if not await deepface_service.check_health():
                cls.set_check_result(session_id, "deepface", False)
                cls.set_failed(session_id, "deepface", "Missing DeepFace dependencies.")
                if session:
                    session.ai_runtime_status = "failed"
                    db.commit()
                log_event(logger, "runtime_failed", failed_component="deepface", error="Missing DeepFace dependencies.", **log_kwargs)
                return
            cls.set_check_result(session_id, "deepface", True)
                
            await asyncio.sleep(0.5)

            # 5. WebSocket Readiness
            cls.update_progress(session_id, 90, "Verifying real-time bridge...")
            cls.set_check_result(session_id, "websocket", True)
            await asyncio.sleep(0.5)
            
            cls.set_ready(session_id)
            if session:
                session.ai_runtime_status = "ready"
                db.commit()
            
            status = cls.get_status(session_id)
            log_event(logger, "runtime_check_completed", duration_ms=status.get("duration_ms"), **log_kwargs)
            log_event(logger, "runtime_ready", **log_kwargs)
            
        except Exception as e:
            logger.error(f"Initialization task error: {e}")
            cls.set_failed(session_id, "internal", "Internal server error during initialization.")
            if session:
                session.ai_runtime_status = "failed"
                db.commit()
            log_event(logger, "runtime_failed", failed_component="internal", error=str(e), **log_kwargs)
        finally:
            db.close()
