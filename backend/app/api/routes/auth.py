import secrets
import logging
import datetime
import re
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from app.db.database import get_db
from app.db.models import Recruiter, RefreshToken, AuditLog
from app.core.security import (
    verify_password, hash_password, create_access_token, 
    generate_refresh_token, hash_refresh_token
)
from app.api.deps import get_current_user
from app.services.email import send_password_reset
from app.core.config import settings
from app.core.rate_limit import limiter

router = APIRouter()
logger = logging.getLogger(__name__)

RESET_TOKEN_EXPIRY_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


class RegisterRequest(BaseModel):
    full_name: str
    email: EmailStr
    password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

def validate_password_policy(password: str):
    if len(password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters")
    if not re.search(r"[A-Z]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one uppercase letter")
    if not re.search(r"[a-z]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one lowercase letter")
    if not re.search(r"\d", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one number")
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        raise HTTPException(status_code=422, detail="Password must contain at least one special character")

def log_audit(db: Session, user_id: str, action: str, ip: str = None, metadata_info: dict = None):
    log = AuditLog(user_id=user_id, action=action, ip_address=ip, metadata_info=metadata_info)
    db.add(log)

@router.post("/auth/login")
@limiter.limit("5/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    recruiter = db.query(Recruiter).filter(Recruiter.email == form_data.username).first()
    client_ip = request.client.host if request.client else None
    
    if not recruiter or not verify_password(form_data.password, recruiter.hashed_password):
        logger.warning("[auth] failed login attempt for %s", form_data.username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not getattr(recruiter, "is_active", True):
        raise HTTPException(status_code=403, detail="Account disabled")
        
    access_token = create_access_token(data={"sub": recruiter.email, "role": recruiter.role.value})
    raw_refresh, hashed_refresh = generate_refresh_token()
    
    # Save refresh token to DB
    rt = RefreshToken(
        user_id=recruiter.id,
        token_hash=hashed_refresh,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(rt)
    
    log_audit(db, recruiter.id, "login", client_ip)
    db.commit()
    
    logger.info("[auth] login successful for %s", recruiter.email)
    
    response.set_cookie(
        key="refresh_token",
        value=raw_refresh,
        httponly=True,
        secure=True, # Ensure HTTPS in prod
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth"
    )
    return {"access_token": access_token, "token_type": "bearer", "role": recruiter.role}


@router.post("/auth/refresh")
def refresh_token(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db)
):
    if not refresh_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing refresh token")
        
    token_hash = hash_refresh_token(refresh_token)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    
    if not rt:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
        
    if rt.revoked or rt.expires_at < datetime.datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")
        
    user = rt.user
    if not user or not getattr(user, "is_active", True):
        raise HTTPException(status_code=403, detail="User account disabled")
        
    # Rotate token
    rt.revoked = True
    new_raw, new_hashed = generate_refresh_token()
    
    new_rt = RefreshToken(
        user_id=user.id,
        token_hash=new_hashed,
        expires_at=datetime.datetime.utcnow() + datetime.timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    )
    db.add(new_rt)
    db.commit()
    
    access_token = create_access_token(data={"sub": user.email, "role": user.role.value})
    
    response.set_cookie(
        key="refresh_token",
        value=new_raw,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
        path="/api/auth"
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/auth/logout")
def logout(
    request: Request,
    response: Response,
    refresh_token: str = Cookie(None),
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user)
):
    if refresh_token:
        token_hash = hash_refresh_token(refresh_token)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
        if rt and rt.user_id == current_user.id:
            rt.revoked = True
            db.commit()
            
    client_ip = request.client.host if request.client else None
    log_audit(db, current_user.id, "logout", client_ip)
    db.commit()
    
    response.delete_cookie(key="refresh_token", path="/api/auth")
    return {"message": "Logged out successfully"}

@router.post("/auth/logout-all")
def logout_all(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: Recruiter = Depends(get_current_user)
):
    db.query(RefreshToken).filter(RefreshToken.user_id == current_user.id).update({"revoked": True})
    
    client_ip = request.client.host if request.client else None
    log_audit(db, current_user.id, "logout_all", client_ip)
    db.commit()
    
    response.delete_cookie(key="refresh_token", path="/api/auth")
    return {"message": "All devices logged out"}


@router.post("/auth/register", status_code=201)
@limiter.limit("3/minute")
def register(request: Request, payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    validate_password_policy(payload.password)

    recruiter = Recruiter(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(recruiter)
    db.commit()
    db.refresh(recruiter)
    
    client_ip = request.client.host if request.client else None
    log_audit(db, recruiter.id, "register", client_ip)
    db.commit()
    
    logger.info("[auth] registered new recruiter: %s", payload.email)
    return {"message": "Account created", "email": payload.email}


@router.post("/auth/forgot-password")
async def forgot_password(request: Request, payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(Recruiter.email == payload.email).first()
    if recruiter:
        token = secrets.token_urlsafe(32)
        recruiter.reset_token = token
        recruiter.reset_token_expiry = (
            datetime.datetime.utcnow() + datetime.timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)
        )
        
        client_ip = request.client.host if request.client else None
        log_audit(db, recruiter.id, "forgot_password", client_ip)
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
def reset_password(request: Request, payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    recruiter = db.query(Recruiter).filter(
        Recruiter.reset_token == payload.token
    ).first()

    if not recruiter:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    if recruiter.reset_token_expiry < datetime.datetime.utcnow():
        raise HTTPException(status_code=400, detail="Reset token has expired")

    validate_password_policy(payload.new_password)

    recruiter.hashed_password = hash_password(payload.new_password)
    recruiter.reset_token = None
    recruiter.reset_token_expiry = None
    
    # Invalidate all refresh tokens to force re-login on all devices
    db.query(RefreshToken).filter(RefreshToken.user_id == recruiter.id).update({"revoked": True})
    
    client_ip = request.client.host if request.client else None
    log_audit(db, recruiter.id, "reset_password", client_ip)
    db.commit()

    logger.info("[auth] password reset successful for %s", recruiter.email)
    return {"message": "Password updated successfully"}