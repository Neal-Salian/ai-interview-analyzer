import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import Recruiter
from app.core.security import verify_password, create_access_token

router = APIRouter()
loggger = logging.getLogger(__name__)

@router.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Recruiter login. Returns a JWT access token.
    Uses OAuth2PasswordRequestForm so it works directly
    with FastAPI's built-in /docs Authorize button.
    """
    recruiter = db.query(Recruiter).filter(
        Recruiter.email == form_data.username
    ).first()

    if not recruiter or not verify_password(form_data.password, recruiter.hashed_password):
        logger.warning(f"[auth] failed login attempt for {form_data.username}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(data={"sub": recruiter.email})
    logger.info(f"[auth] login successful for {recruiter.email}")
    return {"access_token": token, "token_type": "bearer"}