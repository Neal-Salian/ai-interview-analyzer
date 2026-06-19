import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, ConfigDict
from uuid import UUID

from app.db.database import get_db
from app.db.models import Recruiter, UserRole
from app.api.deps import require_admin
from app.api.routes.auth import log_audit

router = APIRouter()
logger = logging.getLogger(__name__)

class UserResponse(BaseModel):
    id: UUID
    email: str
    full_name: Optional[str]
    role: UserRole
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class RoleUpdateRequest(BaseModel):
    role: UserRole

@router.get("/admin/users", response_model=List[UserResponse])
def get_all_users(
    db: Session = Depends(get_db),
    current_admin: Recruiter = Depends(require_admin)
):
    users = db.query(Recruiter).all()
    return users

@router.get("/admin/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Recruiter = Depends(require_admin)
):
    user = db.query(Recruiter).filter(Recruiter.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.patch("/admin/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    request: Request,
    user_id: UUID,
    payload: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: Recruiter = Depends(require_admin)
):
    user = db.query(Recruiter).filter(Recruiter.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    old_role = user.role
    user.role = payload.role
    
    client_ip = request.client.host if request.client else None
    log_audit(db, current_admin.id, "update_role", client_ip, {"target_user_id": str(user_id), "old_role": old_role, "new_role": payload.role})
    db.commit()
    db.refresh(user)
    return user

@router.patch("/admin/users/{user_id}/disable", response_model=UserResponse)
def disable_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Recruiter = Depends(require_admin)
):
    user = db.query(Recruiter).filter(Recruiter.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if user.id == current_admin.id:
        raise HTTPException(status_code=400, detail="Cannot disable yourself")
        
    user.is_active = False
    
    client_ip = request.client.host if request.client else None
    log_audit(db, current_admin.id, "disable_user", client_ip, {"target_user_id": str(user_id)})
    db.commit()
    db.refresh(user)
    return user

@router.patch("/admin/users/{user_id}/enable", response_model=UserResponse)
def enable_user(
    request: Request,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Recruiter = Depends(require_admin)
):
    user = db.query(Recruiter).filter(Recruiter.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_active = True
    
    client_ip = request.client.host if request.client else None
    log_audit(db, current_admin.id, "enable_user", client_ip, {"target_user_id": str(user_id)})
    db.commit()
    db.refresh(user)
    return user
