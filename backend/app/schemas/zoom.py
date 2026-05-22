from pydantic import BaseModel
from typing import Optional

class ZoomParticipant(BaseModel):
    user_id: str
    user_name: str
    email: Optional[str] = None

class ZoomMeetingObject(BaseModel):
    id: str  # Zoom meeting ID
    uuid: str
    host_id: str
    participant: Optional[ZoomParticipant] = None

class ZoomWebhookPayload(BaseModel):
    event: str
    payload: dict