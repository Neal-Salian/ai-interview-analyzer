import base64
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

def _get_fernet() -> Fernet:
    key = settings.ZOOM_TOKEN_ENCRYPTION_KEY
    if not key:
        raise ValueError("ZOOM_TOKEN_ENCRYPTION_KEY is not configured.")
    # In case it's not exactly 32 bytes or base64 url-safe, Fernet will raise ValueError on init.
    # It must be a URL-safe base64-encoded 32-byte key.
    return Fernet(key.encode('utf-8'))

def encrypt_zoom_token(token: str) -> str:
    """Encrypts a plaintext Zoom token using Fernet."""
    if not token:
        return ""
    f = _get_fernet()
    encrypted_bytes = f.encrypt(token.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_zoom_token(encrypted_token: str) -> str:
    """Decrypts an encrypted Zoom token using Fernet."""
    if not encrypted_token:
        return ""
    f = _get_fernet()
    try:
        decrypted_bytes = f.decrypt(encrypted_token.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except InvalidToken:
        logger.error("Failed to decrypt Zoom token. The encryption key may have changed or the token is corrupted.")
        raise ValueError("Invalid or corrupted encrypted Zoom token.")
