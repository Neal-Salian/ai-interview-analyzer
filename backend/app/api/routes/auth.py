import secrets
import logging
import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.db.models import Recruiter
from app.core.security import verify_password, hash_password, create_access_token
from app.services.email import send_password_reset
from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRY_MINUTES = 30


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str


@router.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    recruiter = db.query(Recruiter).filter(Recruiter.email == form_data.username).first()
    if not recruiter or not verify_password(form_data.password, recruiter.hashed_password):
        logger.warning("[auth] failed login attempt for %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = create_access_token(data={"sub": recruiter.email})
    logger.info("[auth] login successful for %s", recruiter.email)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/auth/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    recruiter = Recruiter(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(recruiter)
    db.commit()
    logger.info("[auth] registered new recruiter: %s", payload.email)
    return {"message": "Account created", "email": payload.email}


@router.post("/auth/forgot-password")
async def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    # Always return 200 — never leak whether email exists
    if recruiter:
        token = secrets.token_urlsafe(32)
        recruiter.reset_token = token
        recruiter.reset_token_expiry = (
            datetime.datetime.utcnow() + datetime.timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        )
        db.commit()
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        await send_password_reset(
            to_email=recruiter.email,
            recruiter_name=recruiter.full_name or "",
            reset_url=reset_url,
        )
        logger.info("[auth] password reset email sent to %s", recruiter.email)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(
        Recruiter.reset_token == payload.token
    ).first()

    if not recruiter:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if recruiter.reset_token_expiry < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    if len(payload.new_password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")

    recruiter.hashed_password = hash_password(payload.new_password)
    recruiter.reset_token = None
    recruiter.reset_token_expiry = None
    db.commit()

    logger.info("[auth] password reset successful for %s", recruiter.email)
    return {"message": "Password updated successfully"}