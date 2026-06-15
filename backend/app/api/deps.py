import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Recruiter
from app.core.security import decode_access_token
from app.db.models import Session as InterviewSession
from app.core.config import settings


logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Recruiter:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    payload = decode_access_token(token)
    if not payload:
        raise credentials_exception

    email: str = payload.get("sub")
    if not email:
        raise credentials_exception

    recruiter = db.query(Recruiter).filter(Recruiter.email == email).first()
    if not recruiter:
        raise credentials_exception

    return recruiter


def get_owned_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
) -> InterviewSession:
    """
    Fetch a session and verify the current recruiter owns it.
    Returns 404 for missing sessions (don't leak existence to other recruiters).
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()

    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Enforce ownership strictly. Unowned sessions are inaccessible.
    if session.recruiter_id != current_user.id:
        raise HTTPException(status_code=404, detail="Session not found")  # 404 not 403 — don't leak existence

    return session


def verify_development_env():
    """
    Dependency to restrict access to internal/test endpoints.
    Raises 404 in production to avoid leaking existence of these routes.
    """
    if settings.ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")
    