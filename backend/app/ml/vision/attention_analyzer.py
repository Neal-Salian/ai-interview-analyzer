"""
Attention analyzer — single entry point for the RTMP consumer.

Combines gaze tracking (iris position) + head pose estimation (solvePnP)
into a unified attention verdict. This is the ONLY function the consumer
needs to call. Internally it reuses Face Mesh landmarks between gaze and
head pose to avoid processing the frame twice.

Called from rtmp_consumer.py via asyncio.to_thread(analyze_attention, frame).
"""

import logging
import numpy as np

from app.ml.vision.gaze_tracker import analyze_gaze
from app.ml.vision.head_pose import estimate_head_pose

logger = logging.getLogger(__name__)


def analyze_attention(frame: np.ndarray) -> dict:
    """
    Analyze candidate attention from a single BGR video frame.

    Returns:
        {
            "direction": str,      # center, left, right, up, down, missing
            "confidence": float,   # 0-100
            "yaw": float | None,   # head yaw in degrees
            "pitch": float | None, # head pitch in degrees
            "roll": float | None,  # head roll in degrees
            "face_detected": bool,
            "ear_left": float,     # eye aspect ratio (for integrity reuse)
            "ear_right": float,
        }
    """
    try:
        # Step 1: Gaze analysis (also returns landmarks + EAR)
        gaze = analyze_gaze(frame)

        if gaze["direction"] == "missing":
            return {
                "direction": "missing",
                "confidence": 0.0,
                "yaw": None,
                "pitch": None,
                "roll": None,
                "face_detected": False,
                "ear_left": 0.0,
                "ear_right": 0.0,
            }

        # Step 2: Head pose (reuses landmarks from gaze analysis)
        pose = estimate_head_pose(frame, gaze["landmarks"])

        # Step 3: Combine gaze + pose for refined direction
        direction = _refine_direction(gaze["direction"], pose)
        confidence = _compute_combined_confidence(gaze, pose)

        return {
            "direction": direction,
            "confidence": round(confidence, 1),
            "yaw": pose["yaw"],
            "pitch": pose["pitch"],
            "roll": pose["roll"],
            "face_detected": True,
            "ear_left": gaze["ear_left"],
            "ear_right": gaze["ear_right"],
        }

    except Exception as e:
        logger.warning(f"[ATTENTION] analysis failed: {e}")
        return {
            "direction": "missing",
            "confidence": 0.0,
            "yaw": None,
            "pitch": None,
            "roll": None,
            "face_detected": False,
            "ear_left": 0.0,
            "ear_right": 0.0,
        }


def _refine_direction(gaze_direction: str, pose: dict) -> str:
    """
    Cross-validate gaze direction with head pose.

    If head is turned significantly but eyes say center, head pose wins.
    If eyes say left/right but head is facing center, gaze wins (eyes moved).
    """
    yaw = pose.get("yaw", 0.0)
    pitch = pose.get("pitch", 0.0)

    # Strong head turn overrides gaze
    if abs(yaw) > 25:
        return "left" if yaw < 0 else "right"
    if pitch < -20:
        return "up"
    if pitch > 20:
        return "down"

    # Otherwise trust gaze direction (iris tracking is more precise
    # for subtle eye movements while head stays relatively still)
    return gaze_direction


def _compute_combined_confidence(gaze: dict, pose: dict) -> float:
    """
    Weighted confidence combining gaze confidence + head pose agreement.

    If gaze and head pose agree on direction, confidence is boosted.
    If they disagree, confidence is reduced.
    """
    gaze_conf = gaze.get("confidence", 0.0)
    yaw = abs(pose.get("yaw", 0.0))
    pitch = abs(pose.get("pitch", 0.0))

    # Agreement bonus: if head is facing same direction as gaze
    gaze_dir = gaze.get("direction", "center")
    pose_dir = "center"
    if yaw > 15:
        pose_dir = "right" if pose.get("yaw", 0) > 0 else "left"
    elif pitch > 15:
        pose_dir = "down" if pose.get("pitch", 0) > 0 else "up"

    if gaze_dir == pose_dir:
        # Agreement — boost confidence
        return min(100.0, gaze_conf * 1.1)
    elif gaze_dir == "center" and pose_dir == "center":
        return gaze_conf
    else:
        # Disagreement — slight reduction (ambiguous)
        return max(0.0, gaze_conf * 0.85)
