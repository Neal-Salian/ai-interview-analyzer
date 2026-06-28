from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from datetime import datetime, timezone
import datetime as dt
import asyncio

from app.db.database import get_db
from app.db.models import Recruiter, RecruiterZoomToken
from app.api.deps import get_current_user
from app.services.zoom_api import zoom_api
from app.core.config import settings
from app.core.security import create_access_token, decode_access_token
from app.core.zoom_crypto import encrypt_zoom_token, decrypt_zoom_token

router = APIRouter(prefix="/zoom/oauth", tags=["zoom"])

@router.get("/url")
def get_oauth_url(current_user: Recruiter = Depends(get_current_user)):
    """Returns the Zoom authorization URL for the frontend to redirect to."""
    # Encode recruiter_id in state
    state = create_access_token({"sub": str(current_user.id), "type": "zoom_oauth"}, expires_minutes=15)
    url = zoom_api.get_authorization_url(state=state)
    return {"url": url}

@router.get("/callback")
async def zoom_oauth_callback(code: str, state: str, db: Session = Depends(get_db)):
    """Handles the redirect from Zoom, exchanges code for token, saves to DB."""
    payload = decode_access_token(state)
    if not payload or payload.get("type") != "zoom_oauth":
        raise HTTPException(status_code=400, detail="Invalid or expired state token.")
    
    recruiter_id = payload.get("sub")
    if not recruiter_id:
        raise HTTPException(status_code=400, detail="Invalid state token subject.")

    # Exchange code
    try:
        token_data = await zoom_api.exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to exchange code: {e}")

    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token", "")
    expires_in = token_data.get("expires_in", 3600)
    scope = token_data.get("scope", "")

    if not access_token:
        raise HTTPException(status_code=400, detail="Failed to retrieve access token from Zoom.")

    # Fetch user info from Zoom
    try:
        user_info = await zoom_api.get_user_me(access_token)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch Zoom user profile: {e}")
        
    zoom_user_id = user_info.get("id")
    zoom_email = user_info.get("email")

    if not zoom_user_id:
        raise HTTPException(status_code=400, detail="Zoom API did not return a user ID.")

    # Upsert token
    token_record = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.recruiter_id == recruiter_id).first()
    if not token_record:
        # Check if zoom_user_id is already used by another recruiter
        existing_zoom_user = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.zoom_user_id == zoom_user_id).first()
        if existing_zoom_user and str(existing_zoom_user.recruiter_id) != str(recruiter_id):
            raise HTTPException(status_code=400, detail="This Zoom account is already connected to another recruiter.")
            
        token_record = RecruiterZoomToken(
            recruiter_id=recruiter_id,
            zoom_user_id=zoom_user_id
        )
        db.add(token_record)

    token_record.encrypted_access_token = encrypt_zoom_token(access_token)
    token_record.encrypted_refresh_token = encrypt_zoom_token(refresh_token)
    token_record.expires_at = datetime.utcnow() + dt.timedelta(seconds=expires_in - 60)
    token_record.zoom_user_id = zoom_user_id
    token_record.zoom_email = zoom_email
    token_record.token_scope = scope
    token_record.last_refresh_at = datetime.utcnow()
    db.commit()

    # Redirect to frontend settings or dashboard
    return RedirectResponse(url=f"{settings.FRONTEND_URL}/settings?zoom_connected=true")

@router.get("/status")
def get_zoom_status(current_user: Recruiter = Depends(get_current_user), db: Session = Depends(get_db)):
    token_record = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.recruiter_id == current_user.id).first()
    if not token_record:
        return {"connected": False}
    return {
        "connected": True,
        "zoom_email": token_record.zoom_email,
        "connected_at": token_record.connected_at
    }

@router.delete("/disconnect")
async def disconnect_zoom(current_user: Recruiter = Depends(get_current_user), db: Session = Depends(get_db)):
    token_record = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.recruiter_id == current_user.id).first()
    if not token_record:
        return {"status": "already disconnected"}
        
    access_token = decrypt_zoom_token(token_record.encrypted_access_token)
    # Fire and forget revocation (don't wait/fail if Zoom returns error)
    asyncio.create_task(zoom_api.revoke_token(access_token))
    
    db.delete(token_record)
    db.commit()
    
    return {"status": "disconnected"}
