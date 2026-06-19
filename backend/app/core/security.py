from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.core.config import settings
import secrets
import hashlib

pwd_context = CryptContext(schemes=["argon2", "bcrypt"], deprecated="auto")

def hash_password(password: str) -> str:
    return pwd_context.hash(password[:72].encode('utf-8').decode('utf-8'))

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain[:72], hashed)

def create_access_token(data: dict, expires_minutes: int = 60) -> str:
    payload = data.copy()
    now = datetime.utcnow()
    payload.update({
        "exp": now + timedelta(minutes=expires_minutes),
        "iat": now,
        "nbf": now,
        "iss": "ai-interview-analyzer",
        "aud": "ai-interview-analyzer-client"
    })
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(
            token, 
            settings.SECRET_KEY, 
            algorithms=[settings.ALGORITHM],
            issuer="ai-interview-analyzer",
            audience="ai-interview-analyzer-client"
        )
    except JWTError:
        return None

def generate_refresh_token() -> tuple[str, str]:
    """
    Returns (raw_token, token_hash)
    raw_token is sent to the client (in an HttpOnly cookie).
    token_hash is stored in the database.
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    return raw_token, token_hash

def hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()