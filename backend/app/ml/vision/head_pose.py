"""
Head pose estimation via solvePnP.

Uses 6 facial landmarks from MediaPipe Face Mesh to estimate
the 3D orientation (yaw, pitch, roll) of the head.

Reuses landmarks already computed by gaze_tracker.py to avoid
running Face Mesh twice on the same frame.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# 3D model points — standard face proportions (generic, unitless)
# These correspond to: nose tip, chin, left eye outer, right eye outer,
# left mouth corner, right mouth corner
_MODEL_POINTS = np.array([
    (0.0, 0.0, 0.0),          # Nose tip
    (0.0, -330.0, -65.0),     # Chin
    (-225.0, 170.0, -135.0),  # Left eye left corner
    (225.0, 170.0, -135.0),   # Right eye right corner
    (-150.0, -150.0, -125.0), # Left mouth corner
    (150.0, -150.0, -125.0),  # Right mouth corner
], dtype=np.float64)

# MediaPipe landmark indices for the 6 points above
_LANDMARK_INDICES = [1, 152, 33, 263, 61, 291]


def estimate_head_pose(frame: np.ndarray, landmarks) -> dict:
    """
    Estimate head pose (yaw, pitch, roll) from MediaPipe landmarks.

    Args:
        frame: BGR video frame (used only for dimensions)
        landmarks: MediaPipe face_landmarks object from gaze_tracker.py

    Returns:
        {"yaw": float, "pitch": float, "roll": float}
        Angles in degrees. Yaw: left(-) / right(+).
        Pitch: up(-) / down(+). Roll: tilt left(-) / right(+).
    """
    import cv2

    if landmarks is None:
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

    h, w, _ = frame.shape

    # Extract 2D image points from landmarks
    image_points = np.array([
        (landmarks.landmark[idx].x * w, landmarks.landmark[idx].y * h)
        for idx in _LANDMARK_INDICES
    ], dtype=np.float64)

    # Camera matrix (approximate intrinsic parameters)
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([
        [focal_length, 0, center[0]],
        [0, focal_length, center[1]],
        [0, 0, 1],
    ], dtype=np.float64)

    # No lens distortion
    dist_coeffs = np.zeros((4, 1))

    # Solve for pose
    success, rotation_vector, translation_vector = cv2.solvePnP(
        _MODEL_POINTS,
        image_points,
        camera_matrix,
        dist_coeffs,
        flags=cv2.SOLVEPNP_ITERATIVE,
    )

    if not success:
        return {"yaw": 0.0, "pitch": 0.0, "roll": 0.0}

    # Convert rotation vector to rotation matrix
    rotation_matrix, _ = cv2.Rodrigues(rotation_vector)

    # Decompose rotation matrix to Euler angles
    # Returns angles in degrees
    proj_matrix = np.hstack((rotation_matrix, translation_vector))
    _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(proj_matrix)

    pitch = float(euler_angles[0][0])
    yaw = float(euler_angles[1][0])
    roll = float(euler_angles[2][0])

    return {
        "yaw": round(yaw, 1),
        "pitch": round(pitch, 1),
        "roll": round(roll, 1),
    }
