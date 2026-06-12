"""
Face counter — detects multiple faces in a frame.

Uses OpenCV's Haar cascade (already installed via opencv-python)
for lightweight face counting. Does not replace DeepFace for
emotion analysis — this is purely for integrity monitoring.

Returns the count of faces detected and their bounding boxes.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Load cascade once at module level (same pattern as detector.py)
_cascade = None


def _get_cascade():
    global _cascade
    if _cascade is None:
        import cv2
        _cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        logger.info("[FACE_COUNT] Haar cascade loaded")
    return _cascade


def count_faces(frame: np.ndarray) -> dict:
    """
    Count the number of faces in a BGR frame.

    Returns:
        {
            "face_count": int,
            "bounding_boxes": list[tuple],  # (x, y, w, h) for each face
        }
    """
    import cv2

    try:
        cascade = _get_cascade()

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = cascade.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(60, 60),
            flags=cv2.CASCADE_SCALE_IMAGE,
        )

        boxes = [(int(x), int(y), int(w), int(h)) for (x, y, w, h) in faces]

        return {
            "face_count": len(boxes),
            "bounding_boxes": boxes,
        }

    except Exception as e:
        logger.warning(f"[FACE_COUNT] detection failed: {e}")
        return {"face_count": 0, "bounding_boxes": []}
