"""
Gaze tracker using MediaPipe Face Mesh.

Uses iris landmarks (468-477) and eye corner landmarks to compute
gaze direction. The Face Mesh model is loaded once at import time,
following the same pattern as detector.py.

Returns gaze direction: center, left, right, up, down, or missing.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Lazy-load mediapipe to avoid import-time crash if not installed
_face_mesh = None


def _get_face_mesh():
    """Load MediaPipe Face Mesh once on first call."""
    global _face_mesh
    if _face_mesh is None:
        import mediapipe as mp
        _face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=False,
            max_num_faces=1,
            refine_landmarks=True,  # enables iris landmarks (468-477)
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        logger.info("[GAZE] MediaPipe Face Mesh loaded (with iris refinement)")
    return _face_mesh


# ── Landmark indices ─────────────────────────────────────────────────────────
# Iris centers
LEFT_IRIS_CENTER = 468     # left iris center (from camera perspective)
RIGHT_IRIS_CENTER = 473    # right iris center

# Eye corners (for computing relative iris position)
LEFT_EYE_INNER = 133
LEFT_EYE_OUTER = 33
RIGHT_EYE_INNER = 362
RIGHT_EYE_OUTER = 263

# Upper/lower eyelid (for EAR — used by integrity/liveness)
LEFT_EYE_TOP = 159
LEFT_EYE_BOTTOM = 145
RIGHT_EYE_TOP = 386
RIGHT_EYE_BOTTOM = 374


def analyze_gaze(frame: np.ndarray) -> dict:
    """
    Analyze gaze direction from a BGR video frame.

    Returns:
        {
            "direction": "center" | "left" | "right" | "up" | "down" | "missing",
            "confidence": float (0-100),
            "iris_ratio_h": float,  # horizontal iris position (0=left, 1=right)
            "iris_ratio_v": float,  # vertical iris position (0=top, 1=bottom)
            "landmarks": list | None,  # raw landmarks for reuse by head_pose/liveness
            "ear_left": float,   # eye aspect ratio (for blink detection)
            "ear_right": float,
        }
    """
    import cv2

    try:
        face_mesh = _get_face_mesh()
    except ImportError:
        logger.warning("[GAZE] mediapipe not installed — returning missing")
        return _missing_result()

    # MediaPipe expects RGB
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = face_mesh.process(rgb)

    if not results.multi_face_landmarks:
        return _missing_result()

    landmarks = results.multi_face_landmarks[0]
    h, w, _ = frame.shape

    # Convert landmarks to pixel coordinates
    def lm(idx):
        pt = landmarks.landmark[idx]
        return np.array([pt.x * w, pt.y * h])

    # ── Horizontal gaze (iris position relative to eye width) ────────────
    # Left eye (from camera perspective)
    left_inner = lm(LEFT_EYE_INNER)
    left_outer = lm(LEFT_EYE_OUTER)
    left_iris = lm(LEFT_IRIS_CENTER)
    left_eye_width = np.linalg.norm(left_inner - left_outer)

    # Right eye
    right_inner = lm(RIGHT_EYE_INNER)
    right_outer = lm(RIGHT_EYE_OUTER)
    right_iris = lm(RIGHT_IRIS_CENTER)
    right_eye_width = np.linalg.norm(right_inner - right_outer)

    if left_eye_width < 1 or right_eye_width < 1:
        return _missing_result()

    # Iris position as ratio within eye (0 = outer, 1 = inner)
    left_ratio_h = np.linalg.norm(left_iris - left_outer) / left_eye_width
    right_ratio_h = np.linalg.norm(right_iris - right_outer) / right_eye_width
    avg_ratio_h = (left_ratio_h + right_ratio_h) / 2

    # ── Vertical gaze ────────────────────────────────────────────────────
    left_top = lm(LEFT_EYE_TOP)
    left_bottom = lm(LEFT_EYE_BOTTOM)
    right_top = lm(RIGHT_EYE_TOP)
    right_bottom = lm(RIGHT_EYE_BOTTOM)

    left_eye_height = np.linalg.norm(left_top - left_bottom)
    right_eye_height = np.linalg.norm(right_top - right_bottom)

    if left_eye_height < 1 or right_eye_height < 1:
        left_ratio_v = 0.5
        right_ratio_v = 0.5
    else:
        left_ratio_v = np.linalg.norm(left_iris - left_top) / left_eye_height
        right_ratio_v = np.linalg.norm(right_iris - right_top) / right_eye_height
    avg_ratio_v = (left_ratio_v + right_ratio_v) / 2

    # ── Eye Aspect Ratio (for blink detection in liveness module) ────────
    ear_left = _compute_ear(lm, LEFT_EYE_TOP, LEFT_EYE_BOTTOM,
                            LEFT_EYE_INNER, LEFT_EYE_OUTER)
    ear_right = _compute_ear(lm, RIGHT_EYE_TOP, RIGHT_EYE_BOTTOM,
                             RIGHT_EYE_INNER, RIGHT_EYE_OUTER)

    # ── Classify direction ───────────────────────────────────────────────
    direction = _classify_direction(avg_ratio_h, avg_ratio_v)

    # Confidence: higher when iris is clearly in a position
    # Center has highest confidence when ratio is near 0.5
    if direction == "center":
        h_dev = abs(avg_ratio_h - 0.5)
        v_dev = abs(avg_ratio_v - 0.5)
        confidence = max(0, 100 - (h_dev + v_dev) * 200)
    else:
        confidence = min(100, abs(avg_ratio_h - 0.5) * 200 + 40)

    return {
        "direction": direction,
        "confidence": round(confidence, 1),
        "iris_ratio_h": round(avg_ratio_h, 3),
        "iris_ratio_v": round(avg_ratio_v, 3),
        "landmarks": landmarks,
        "ear_left": round(ear_left, 3),
        "ear_right": round(ear_right, 3),
    }


def _classify_direction(h_ratio: float, v_ratio: float) -> str:
    """
    Classify gaze direction from iris position ratios.
    h_ratio: 0 = looking left, 0.5 = center, 1 = looking right
    v_ratio: 0 = looking up, 0.5 = center, 1 = looking down
    """
    # Thresholds (calibrated for typical webcam distance)
    H_CENTER_MIN, H_CENTER_MAX = 0.35, 0.65
    V_CENTER_MIN, V_CENTER_MAX = 0.30, 0.70

    if h_ratio < H_CENTER_MIN:
        return "left"
    if h_ratio > H_CENTER_MAX:
        return "right"
    if v_ratio < V_CENTER_MIN:
        return "up"
    if v_ratio > V_CENTER_MAX:
        return "down"
    return "center"


def _compute_ear(lm_func, top_idx, bottom_idx, inner_idx, outer_idx) -> float:
    """
    Eye Aspect Ratio — ratio of eye height to width.
    Low EAR = eye closed (blink). Used by integrity/liveness module.
    """
    top = lm_func(top_idx)
    bottom = lm_func(bottom_idx)
    inner = lm_func(inner_idx)
    outer = lm_func(outer_idx)

    height = np.linalg.norm(top - bottom)
    width = np.linalg.norm(inner - outer)

    if width < 1:
        return 0.0
    return height / width


def _missing_result() -> dict:
    return {
        "direction": "missing",
        "confidence": 0.0,
        "iris_ratio_h": 0.0,
        "iris_ratio_v": 0.0,
        "landmarks": None,
        "ear_left": 0.0,
        "ear_right": 0.0,
    }
