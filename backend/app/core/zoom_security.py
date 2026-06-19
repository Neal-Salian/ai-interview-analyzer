import hashlib
import hmac
import time
import logging

logger = logging.getLogger(__name__)

TIMESTAMP_TOLERANCE_SECONDS = 300  # 5 minutes


def verify_zoom_signature(
    raw_body: bytes,
    zoom_signature: str,
    zoom_timestamp: str,
    secret: str,
) -> bool:
    """
    Verifies a Zoom webhook request using HMAC-SHA256.

    Zoom signs requests as:
        HMAC-SHA256(secret, f"v0:{timestamp}:{raw_body}")
    and sends the result as:
        x-zm-signature: v0=<hex_digest>

    Also rejects requests older than 5 minutes to prevent replay attacks.
    """
    # Reject stale requests
    try:
        request_time = int(zoom_timestamp)
    except (ValueError, TypeError):
        logger.warning("[ZOOM] Invalid timestamp header")
        return False

    age = abs(time.time() - request_time)
    if age > TIMESTAMP_TOLERANCE_SECONDS:
        logger.warning(f"[ZOOM] Rejected stale webhook (age={age:.0f}s)")
        return False

    # Recompute signature
    message = f"v0:{zoom_timestamp}:{raw_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    # Constant-time comparison prevents timing attacks
    if not hmac.compare_digest(expected, zoom_signature):
        logger.warning("[ZOOM] Signature mismatch — possible spoofed request")
        return False

    return True