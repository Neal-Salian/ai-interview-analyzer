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
            cls._state[session_id]["status"] = "ready"
            cls._state[session_id]["progress"] = 100
            cls._state[session_id]["current_step"] = "AI engine ready."
            start_time = cls._state[session_id].get("start_time", time.time())
            cls._state[session_id]["duration_ms"] = int((time.time() - start_time) * 1000)

    @classmethod
    def set_failed(cls, session_id: str, failed_component: str, error_msg: str):
        """Mark initialization as failed with specific component."""
        if session_id in cls._state:
            cls._state[session_id]["status"] = "failed"
            cls._state[session_id]["failed_component"] = failed_component
            cls._state[session_id]["current_step"] = error_msg
            start_time = cls._state[session_id].get("start_time", time.time())
            cls._state[session_id]["duration_ms"] = int((time.time() - start_time) * 1000)

    @classmethod
    def start_analysis(cls, session_id: str, db=None, session_model=None, recruiter_id: str = None) -> bool:
        """Transition runtime from READY to RUNNING. Returns True on success."""
        state = cls._state.get(session_id)
        if not state:
            return False
        # Only allow transition from ready
        if state.get("status") != "ready":
            return False
            
        state["status"] = "running"
        state["current_step"] = "AI analysis running."
        state["progress"] = 100
        
        # Isolate runtime persistence here
        if db and session_model:
            session_model.ai_runtime_status = "running"
            db.commit()
            db.refresh(session_model)
            
        from app.core.logging_config import log_event
        log_kwargs = {"session_id": session_id}
        if recruiter_id:
            log_kwargs["recruiter_id"] = recruiter_id
        log_event(logger, "analysis_started", **log_kwargs)
        return True

    @classmethod
    def clear(cls, session_id: str):
        """Clear state for a session."""
        if session_id in cls._state:
            del cls._state[session_id]
