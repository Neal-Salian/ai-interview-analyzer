"""
Integrity checker — entry point for all integrity checks.

Aggregates face counting, liveness detection, and voice anomaly
detection into a unified result. Called from rtmp_consumer.py
on each video frame.

Returns a list of integrity events (may be empty if all checks pass).
"""

import logging
import datetime
import numpy as np

from app.ml.integrity.face_counter import count_faces
from app.ml.integrity.liveness import check_liveness

logger = logging.getLogger(__name__)

# How many consecutive frames with multiple faces before we alert
MULTI_FACE_ALERT_THRESHOLD = 3

# Liveness alert: how many seconds of no liveness before alerting
LIVENESS_ALERT_AFTER_SECONDS = 45.0


def check_integrity(
    frame: np.ndarray,
    attention_result: dict,
    audio_array: np.ndarray | None = None,
    prev_state: dict | None = None,
) -> dict:
    """
    Run all integrity checks on the current frame + attention data.

    Args:
        frame: BGR video frame
        attention_result: output from analyze_attention()
        audio_array: optional audio data for voice anomaly detection
        prev_state: persistent state from previous frame

    Returns:
        {
            "events": list[dict],     # integrity events to store in DB
            "updated_state": dict,    # pass back as prev_state next frame
        }
    """
    state = dict(prev_state) if prev_state else {}
    if "multi_face_streak" not in state:
        state["multi_face_streak"] = 0
        state["liveness_state"] = {}
        state["liveness_alerted"] = False

    events = []

    # ── 1. Multiple face detection ───────────────────────────────────────
    try:
        face_result = count_faces(frame)
        face_count = face_result["face_count"]

        if face_count > 1:
            state["multi_face_streak"] += 1
            if state["multi_face_streak"] >= MULTI_FACE_ALERT_THRESHOLD:
                events.append({
                    "event_type": "multi_face",
                    "severity": "warning",
                    "details": {
                        "face_count": face_count,
                        "consecutive_frames": state["multi_face_streak"],
                    },
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                })
                # Reset streak after alerting to avoid flooding
                state["multi_face_streak"] = 0
        else:
            state["multi_face_streak"] = 0

    except Exception as e:
        logger.warning(f"[INTEGRITY] face counting failed: {e}")

    # ── 2. Liveness detection ────────────────────────────────────────────
    try:
        liveness = check_liveness(attention_result, state.get("liveness_state", {}))
        state["liveness_state"] = liveness["updated_state"]

        # Alert if not live after threshold period
        if not liveness["is_live"] and liveness["updated_state"].get("frames_seen", 0) > 30:
            if not state.get("liveness_alerted", False):
                events.append({
                    "event_type": "liveness_concern",
                    "severity": "info",
                    "details": {
                        "liveness_score": liveness["liveness_score"],
                        "blinks_detected": liveness["blinks_detected"],
                    },
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                })
                state["liveness_alerted"] = True
        else:
            # Reset alert flag once liveness confirmed
            state["liveness_alerted"] = False

    except Exception as e:
        logger.warning(f"[INTEGRITY] liveness check failed: {e}")

    # ── 3. Face missing detection ────────────────────────────────────────
    if not attention_result.get("face_detected", True):
        face_missing_count = state.get("face_missing_streak", 0) + 1
        state["face_missing_streak"] = face_missing_count

        # Alert after 10 consecutive frames with no face
        if face_missing_count == 10:
            events.append({
                "event_type": "face_missing",
                "severity": "warning",
                "details": {
                    "consecutive_frames": face_missing_count,
                },
                "timestamp": datetime.datetime.utcnow().isoformat(),
            })
    else:
        state["face_missing_streak"] = 0

    # ── 4. Voice anomaly detection (only if audio provided) ──────────────
    if audio_array is not None:
        try:
            from app.ml.integrity.voice_detector import detect_voice_anomaly
            voice_result = detect_voice_anomaly(audio_array)
            if voice_result["anomaly_detected"]:
                events.append({
                    "event_type": f"voice_{voice_result['anomaly_type']}",
                    "severity": "warning",
                    "details": voice_result["details"],
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                })
        except Exception as e:
            logger.warning(f"[INTEGRITY] voice detection failed: {e}")

    return {
        "events": events,
        "updated_state": state,
    }
