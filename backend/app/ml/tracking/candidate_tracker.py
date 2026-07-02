"""
Candidate Face Tracker — enrollment, verification, and tracking.

Handles:
  - Atomic enrollment from high-quality frames (DeepFace embedding)
  - Event-driven re-identification (DeepFace verification)
  - Lightweight OpenCV tracking between verifications
  - Confidence hysteresis (acquire/release thresholds)
  - Graceful fallback when tracker degrades at low FPS

This module is consumed exclusively by rtmp_consumer.py.
It does NOT store state — all state lives in RuntimeManager.
The OpenCV tracker instance is held locally by the consumer.

No database interaction. No persistent biometric storage.
"""

import time
import logging
import numpy as np
from enum import Enum
from typing import Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)

try:
    from deepface import DeepFace
except ImportError:
    DeepFace = None

try:
    from deepface.commons import distance as dst
except ImportError:
    dst = None

# ── Tracking State Machine ───────────────────────────────────────────────────

class TrackingStatus(str, Enum):
    NOT_ENROLLED = "not_enrolled"
    ENROLLING = "enrolling"
    TRACKING = "tracking"
    LOST = "lost"
    REVERIFYING = "reverifying"
    SESSION_ENDED = "session_ended"


# ── DeepFace Model Cache ────────────────────────────────────────────────────
# Loaded once per process to avoid repeated model initialization overhead.

_deepface_model_name = "VGG-Face"
_deepface_detector = "opencv"
_deepface_model_loaded = False
import threading
_deepface_lock = threading.Lock()


def _ensure_deepface_model():
    """Pre-load the DeepFace recognition model into memory (idempotent)."""
    global _deepface_model_loaded
    if _deepface_model_loaded or DeepFace is None:
        return
    with _deepface_lock:
        if _deepface_model_loaded:
            return
        try:
            import os
            weights_path = os.path.expanduser("~/.deepface/weights/vgg_face_weights.h5")
            if not os.path.exists(weights_path):
                raise FileNotFoundError(f"DeepFace weights not found at {weights_path}. Automatic download disabled.")
                
            # Build the model once — subsequent calls reuse the cached instance
            DeepFace.build_model(_deepface_model_name)
            _deepface_model_loaded = True
            logger.info("[TRACKER] DeepFace recognition model pre-loaded")
        except Exception as e:
            logger.warning(f"[TRACKER] Failed to pre-load DeepFace model: {e}")


# ── Tracking Metadata Factory ───────────────────────────────────────────────

def create_tracking_metadata() -> dict:
    """Create a fresh tracking_metadata dict for a new session."""
    return {
        "tracking_status": TrackingStatus.NOT_ENROLLED,
        "candidate_embedding": None,
        "last_known_bbox": None,
        "last_verified_timestamp": None,
        "confidence": 0.0,
        "enrollment_start_time": None,
        # ── Operational statistics ─────────────────────────────────────
        "successful_tracking_duration_sec": 0.0,
        "reidentification_count": 0,
        "tracking_failure_count": 0,
        "confidence_sum": 0.0,
        "confidence_samples": 0,
        # ── Cooldown state ─────────────────────────────────────────────
        "frames_since_last_verify": 0,
        "consecutive_verify_failures": 0,
        # ── Stabilisation counter ──────────────────────────────────────
        "stabilisation_frames_remaining": 0,
        # ── Tracking timeline marker ───────────────────────────────────
        "tracking_acquired_at": None,
        # ── Enrollment ─────────────────────────────────────────────────
        "enrollment_error": None,
    }


# ── Enrollment ──────────────────────────────────────────────────────────────

# Quality gate constants
MIN_FACE_AREA_RATIO = 0.02       # Face must occupy ≥2% of frame area
MIN_SHARPNESS = 50.0             # Laplacian variance threshold
ENROLLMENT_FRAMES_TARGET = 3     # Capture up to 3 good frames
STABILISATION_FRAMES = 2         # Wait 2 frames after enrollment


def assess_frame_quality(frame: np.ndarray, face_region: dict) -> bool:
    """
    Determine whether a detected face meets enrollment quality criteria.

    Checks:
      - Face occupies a minimum percentage of the frame.
      - Face region is not excessively blurry.
    """
    import cv2

    frame_h, frame_w = frame.shape[:2]
    frame_area = frame_h * frame_w

    fx, fy = face_region.get("x", 0), face_region.get("y", 0)
    fw, fh = face_region.get("w", 0), face_region.get("h", 0)
    face_area = fw * fh

    # Area ratio check
    if face_area / max(frame_area, 1) < MIN_FACE_AREA_RATIO:
        return False

    # Sharpness check (Laplacian variance on the face crop)
    x1 = max(0, fx)
    y1 = max(0, fy)
    x2 = min(frame_w, fx + fw)
    y2 = min(frame_h, fy + fh)
    crop = frame[y1:y2, x1:x2]

    if crop.size == 0:
        return False

    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()

    if sharpness < MIN_SHARPNESS:
        return False

    return True


def generate_embedding(frame: np.ndarray) -> Optional[list]:
    """
    Generate a face embedding from a single frame using DeepFace.

    Returns the embedding vector, or None if no face is detected.
    """
    _ensure_deepface_model()
    try:
        if DeepFace is None:
            return None

        results = DeepFace.represent(
            img_path=frame,
            model_name=_deepface_model_name,
            detector_backend=_deepface_detector,
            enforce_detection=False,
        )
        if results and len(results) > 0:
            return results[0]["embedding"]
        return None
    except Exception as e:
        logger.warning(f"[TRACKER] Embedding generation failed: {e}")
        return None


@dataclass
class EnrollmentResult:
    success: bool
    reason: str
    embedding: Optional[list] = None
    bbox: Optional[tuple] = None


def enroll_from_frames(frames: list[np.ndarray]) -> EnrollmentResult:
    """
    Perform atomic enrollment from a batch of captured frames.

    Steps:
      1. For each frame, detect faces and apply quality filters.
      2. Enforce exactly one face per frame.
      3. Generate embeddings for accepted frames.
      4. Average the embeddings to produce a robust reference.

    Returns:
        EnrollmentResult object containing success status, reason, and optionally embedding/bbox.
    """
    _ensure_deepface_model()
    if DeepFace is None:
        return EnrollmentResult(success=False, reason="deepface_not_available")

    embeddings = []
    best_bbox = None
    
    counts = {
        "no_face_detected": 0,
        "multiple_faces_detected": 0,
        "insufficient_quality": 0
    }

    for i, frame in enumerate(frames):
        try:
            import inspect
            session_id = "unknown"
            try:
                # Attempt to extract session_id from the caller's frame (rtmp_consumer.py)
                caller_locals = inspect.currentframe().f_back.f_back.f_locals
                if "session_id" in caller_locals:
                    session_id = caller_locals["session_id"]
            except Exception:
                pass

            frame_size = f"{frame.shape[1]}x{frame.shape[0]}"
            detector_backend = _deepface_detector
            model_name = _deepface_model_name
            
            # Get number of detected faces before calling represent
            num_detected_faces = 0
            try:
                faces = DeepFace.extract_faces(
                    img_path=frame,
                    detector_backend=detector_backend,
                    enforce_detection=False,
                )
                num_detected_faces = len(faces)
            except Exception:
                num_detected_faces = -1
                
            logger.info(
                f"[TRACKER] Before represent | session_id: {session_id} | "
                f"frame_size: {frame_size} | detector_backend: {detector_backend} | "
                f"model_name: {model_name} | number of detected faces: {num_detected_faces}"
            )

            results = DeepFace.represent(
                img_path=frame,
                model_name=model_name,
                detector_backend=detector_backend,
                enforce_detection=False,
            )

            if not results or len(results) == 0:
                logger.warning(f"[TRACKER] Frame {i}: No face detected by DeepFace")
                counts["no_face_detected"] += 1
                continue

            if len(results) > 1:
                logger.warning(f"[TRACKER] Frame {i}: Multiple faces detected ({len(results)})")
                counts["multiple_faces_detected"] += 1
                continue

            face_region = results[0].get("facial_area", {})

            if not assess_frame_quality(frame, face_region):
                logger.warning(f"[TRACKER] Frame {i}: Failed quality assessment (Region: {face_region})")
                counts["insufficient_quality"] += 1
                continue

            embeddings.append(results[0]["embedding"])

            # Keep the bounding box from the most recent accepted frame
            best_bbox = (
                face_region.get("x", 0),
                face_region.get("y", 0),
                face_region.get("w", 0),
                face_region.get("h", 0),
            )

        except Exception as e:
            import traceback
            import sys
            
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.format_exc()
            
            # Find the exact line that threw the exception
            tb_frame = exc_traceback
            while tb_frame.tb_next:
                tb_frame = tb_frame.tb_next
            exact_file = tb_frame.tb_frame.f_code.co_filename
            exact_line = tb_frame.tb_lineno
            
            logger.error(
                f"DeepFace.represent THREW AN EXCEPTION:\n"
                f"Exception Type: {type(e).__name__}\n"
                f"Exception Message: {str(e)}\n"
                f"Exact File: {exact_file}\n"
                f"Exact Line: {exact_line}\n"
                f"Complete Traceback:\n{tb}"
            )
            raise e

    if not embeddings:
        logger.warning(f"[TRACKER] Enrollment failed. Rejection counts: {counts}")
        
        # Determine primary reason for failure based on counts
        if counts["multiple_faces_detected"] > 0:
            return EnrollmentResult(success=False, reason="multiple_faces_detected")
        elif counts["insufficient_quality"] > 0:
            return EnrollmentResult(success=False, reason="insufficient_quality")
        else:
            return EnrollmentResult(success=False, reason="no_face_detected")

    # Average the embeddings for robustness
    avg_embedding = np.mean(embeddings, axis=0).tolist()
    logger.info(f"[TRACKER] Enrollment succeeded — averaged {len(embeddings)} embeddings")
    return EnrollmentResult(success=True, reason="success", embedding=avg_embedding, bbox=best_bbox)


# ── Verification ────────────────────────────────────────────────────────────

VERIFY_COOLDOWN_FRAMES = 3  # Minimum frames between re-verification attempts


def verify_candidate(
    frame: np.ndarray,
    candidate_embedding: list,
    acquire_threshold: float,
    release_threshold: float,
    currently_tracking: bool,
) -> Optional[dict]:
    """
    Attempt to identify the enrolled candidate in the current frame.

    Detects all faces, generates embeddings, and compares against the
    enrolled candidate embedding.

    Uses confidence hysteresis:
      - If currently_tracking is False: match must >= acquire_threshold
      - If currently_tracking is True: match must >= release_threshold

    Returns:
        {"bbox": (x, y, w, h), "confidence": float} or None if no match.
    """
    _ensure_deepface_model()
    try:
        if DeepFace is None:
            return None

        results = DeepFace.represent(
            img_path=frame,
            model_name=_deepface_model_name,
            detector_backend=_deepface_detector,
            enforce_detection=False,
        )

        if not results:
            return None

        threshold = release_threshold if currently_tracking else acquire_threshold

        best_match = None
        best_similarity = -1.0

        candidate_np = np.array(candidate_embedding)

        for face in results:
            face_embedding = np.array(face["embedding"])

            # Cosine similarity (1.0 = identical, 0.0 = orthogonal)
            cos_sim = float(np.dot(candidate_np, face_embedding) / (
                np.linalg.norm(candidate_np) * np.linalg.norm(face_embedding) + 1e-10
            ))

            if cos_sim > best_similarity:
                best_similarity = cos_sim
                face_region = face.get("facial_area", {})
                best_match = {
                    "bbox": (
                        face_region.get("x", 0),
                        face_region.get("y", 0),
                        face_region.get("w", 0),
                        face_region.get("h", 0),
                    ),
                    "confidence": cos_sim,
                }

        if best_match and best_match["confidence"] >= threshold:
            return best_match

        return None

    except Exception as e:
        logger.warning(f"[TRACKER] Verification failed: {e}")
        return None


# ── Frame Cropping ──────────────────────────────────────────────────────────

def crop_candidate(frame: np.ndarray, bbox: tuple, padding: float = 0.2) -> np.ndarray:
    """
    Crop the candidate's face region from the frame with optional padding.

    Args:
        frame: Full BGR frame.
        bbox: (x, y, w, h) bounding box.
        padding: Fractional expansion around the bounding box (default 20%).

    Returns:
        Cropped BGR image of the candidate's face.
    """
    h, w = frame.shape[:2]
    x, y, bw, bh = bbox

    pad_w = int(bw * padding)
    pad_h = int(bh * padding)

    x1 = max(0, x - pad_w)
    y1 = max(0, y - pad_h)
    x2 = min(w, x + bw + pad_w)
    y2 = min(h, y + bh + pad_h)

    crop = frame[y1:y2, x1:x2]
    if crop.size == 0:
        return frame  # Fallback to full frame if crop is degenerate
    return crop


# ── OpenCV Tracker Helpers ──────────────────────────────────────────────────

def create_tracker():
    """Create a new OpenCV CSRT tracker instance."""
    import cv2
    return cv2.TrackerCSRT_create()


def init_tracker(tracker, frame: np.ndarray, bbox: tuple):
    """Initialize (or reinitialize) the OpenCV tracker with a bounding box."""
    # OpenCV expects (x, y, w, h)
    tracker.init(frame, bbox)


def update_tracker(tracker, frame: np.ndarray) -> Optional[tuple]:
    """
    Update the tracker with a new frame.

    Returns:
        (x, y, w, h) bounding box if tracking succeeds, else None.
    """
    success, box = tracker.update(frame)
    if success:
        x, y, w, h = [int(v) for v in box]
        return (x, y, w, h)
    return None
