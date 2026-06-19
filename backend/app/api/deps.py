import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Recruiter, UserRole
from app.core.security import decode_access_token
from app.db.models import Session as InterviewSession
from app.core.config import settings


logger = logging.getLogger(__name__)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
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
    if not getattr(recruiter, "is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
    return recruiter

def require_admin(current_user: Recruiter = Depends(get_current_user)) -> Recruiter:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires administrator privileges"
        )
    return current_user

def require_recruiter(current_user: Recruiter = Depends(get_current_user)) -> Recruiter:
    if current_user.role not in (UserRole.ADMIN, UserRole.RECRUITER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Requires recruiter privileges"
        )
    return current_user

def get_owned_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user),
) -> InterviewSession:
    """
    Fetch a session and verify ownership.
    Returns 404 for missing or unauthorised (don't leak existence).
    Webhook-created sessions (recruiter_id=None) are visible to all authenticated recruiters.
    Admins can access all sessions.
    """
    session = db.query(InterviewSession).filter(
        InterviewSession.id == session_id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
        
    if current_user.role != UserRole.ADMIN:
        if session.recruiter_id and session.recruiter_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
    return session


def verify_development_env():
    """
    Dependency to restrict access to internal/test endpoints.
    Raises 404 in production to avoid leaking existence of these routes.
    """
    if settings.ENV != "development":
        raise HTTPException(status_code=404, detail="Not found")
    