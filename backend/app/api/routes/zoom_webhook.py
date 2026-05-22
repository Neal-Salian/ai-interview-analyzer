import hmac
import hashlib
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Any, Dict

from app.core.config import settings
from app.db.database import get_db
from sqlalchemy.orm import Session

router = APIRouter()
class ZoomPayload(BaseModel):
    plainToken: str | None = None  
    object: Dict[str, Any] | None = None 

class ZoomWebhookRequest(BaseModel):
    event: str
    event_ts: int
    payload: ZoomPayload

def verify_zoom_signature(request_body: bytes, timestamp: str, signature: str) -> bool:
    message = f"v0:{timestamp}:{request_body.decode('utf-8')}"
    expected = "v0=" + hmac.new(
        settings.ZOOM_WEBHOOK_SECRET.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)

def generate_handshake_token(plain_token: str) -> str:
    """Hashes the Zoom token specifically for the initial setup handshake"""
    msg = plain_token.encode("utf-8")
    secret = settings.ZOOM_WEBHOOK_SECRET.encode("utf-8")
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


@router.post("/zoom")
async def zoom_webhook(
    request: ZoomWebhookRequest, 
    db: Session = Depends(get_db)
):
    # 1. Endpoint Validation (The Security Handshake)
    if request.event == "endpoint.url_validation":
        if not request.payload.plainToken:
            raise HTTPException(status_code=400, detail="Missing plainToken")
            
            
        encrypted_token = generate_handshake_token(request.payload.plainToken)
        
        return JSONResponse(
            status_code=200,
            content={
                "plainToken": request.payload.plainToken,
                "encryptedToken": encrypted_token
            }
        )

    # 2. Process Actual Meeting Events
    if request.event == "meeting.started":
        # Extract data safely assuming payload.object exists
        meeting_data = request.payload.object or {}
        meeting_id = meeting_data.get("id")
        topic = meeting_data.get("topic")
        
        print(f"SUCCESS: Zoom Meeting '{topic}' (ID: {meeting_id}) just started!")
        
        return JSONResponse(status_code=200, content={"message": "Meeting started event received"})

    return JSONResponse(status_code=200, content={"message": "Event ignored"})