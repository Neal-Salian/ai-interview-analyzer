"""
Liveness detection — blink detection + head movement analysis.

Uses Eye Aspect Ratio (EAR) from gaze_tracker.py output and head
pose changes between consecutive frames to verify the candidate
is a real person and not a static image or video replay.

This module does NOT use any deep learning liveness model — it relies
on observable physical signals: blinks and head micro-movements.
"""

import logging
import time

logger = logging.getLogger(__name__)

# EAR threshold below which we consider the eye "closed"
EAR_BLINK_THRESHOLD = 0.21

# Minimum head movement (degrees) between frames to count as "moved"
HEAD_MOVEMENT_THRESHOLD = 1.5

# Time window for liveness assessment (seconds)
LIVENESS_WINDOW = 30.0

# Minimum blinks in the window for liveness
MIN_BLINKS_FOR_LIVENESS = 2


def check_liveness(attention_result: dict, prev_state: dict) -> dict:
    """
    Assess liveness from attention data (which includes EAR + head pose).

    Args:
        attention_result: output from analyze_attention() — contains
            ear_left, ear_right, yaw, pitch, roll, face_detected
        prev_state: persistent state dict from the previous frame.

    Returns:
        {
            "is_live": bool,
            "liveness_score": float (0-100),
            "blinks_detected": int (total since tracking started),
            "head_moved": bool (this frame vs previous),
            "updated_state": dict (pass back as prev_state next frame),
        }
    """
    now = time.time()

    # Initialize state on first call
    state = dict(prev_state) if prev_state else {}
    if "blink_count" not in state:
        state = {
            "blink_count": 0,
            "eye_was_closed": False,
            "last_yaw": None,
            "last_pitch": None,
            "head_movements": 0,
            "window_start": now,
            "frames_seen": 0,
        }

    state["frames_seen"] += 1

    if not attention_result.get("face_detected", False):
        return {
            "is_live": False,
            "liveness_score": 0.0,
            "blinks_detected": state["blink_count"],
            "head_moved": False,
            "updated_state": state,
        }

    # ── Blink detection via EAR ──────────────────────────────────────────
    ear_left = attention_result.get("ear_left", 0.3)
    ear_right = attention_result.get("ear_right", 0.3)
    avg_ear = (ear_left + ear_right) / 2

    eye_closed = avg_ear < EAR_BLINK_THRESHOLD
    if state["eye_was_closed"] and not eye_closed:
        # Eye just reopened — that's a blink
        state["blink_count"] += 1
    state["eye_was_closed"] = eye_closed

    # ── Head movement detection ──────────────────────────────────────────
    yaw = attention_result.get("yaw") or 0.0
    pitch = attention_result.get("pitch") or 0.0
    head_moved = False

    if state["last_yaw"] is not None:
        delta_yaw = abs(yaw - state["last_yaw"])
        delta_pitch = abs(pitch - state["last_pitch"])
        if delta_yaw > HEAD_MOVEMENT_THRESHOLD or delta_pitch > HEAD_MOVEMENT_THRESHOLD:
            head_moved = True
            state["head_movements"] += 1

    state["last_yaw"] = yaw
    state["last_pitch"] = pitch

    # ── Liveness score ───────────────────────────────────────────────────
    elapsed = now - state["window_start"]

    if elapsed < 5.0:
        # Not enough data yet — assume live
        liveness_score = 50.0
        is_live = True
    else:
        # Score based on blink rate and head movement
        blink_score = min(50.0, state["blink_count"] * 15.0)
        movement_score = min(50.0, state["head_movements"] * 5.0)
        liveness_score = blink_score + movement_score

        is_live = (
            state["blink_count"] >= MIN_BLINKS_FOR_LIVENESS
            or state["head_movements"] >= 3
        )

    # Reset window periodically to keep scores current
    if elapsed > LIVENESS_WINDOW:
        state["blink_count"] = 0
        state["head_movements"] = 0
        state["window_start"] = now

    return {
        "is_live": is_live,
        "liveness_score": round(min(100.0, liveness_score), 1),
        "blinks_detected": state["blink_count"],
        "head_moved": head_moved,
        "updated_state": state,
    }
