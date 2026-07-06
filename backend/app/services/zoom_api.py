"""
Zoom Authorization Code OAuth API Service.

Handles:
  - Per-recruiter OAuth token acquisition and refresh
  - Meeting creation and deletion using the recruiter's specific token
"""
import time
import base64
import logging
from dataclasses import dataclass
from typing import Optional
from datetime import datetime, timezone
import datetime as dt

import httpx
from sqlalchemy.orm import Session as DBSession

from app.core.config import settings
from app.db.models import RecruiterZoomToken
from app.core.zoom_crypto import encrypt_zoom_token, decrypt_zoom_token

logger = logging.getLogger(__name__)

class ZoomAPIError(Exception):
    def __init__(self, status_code: int, detail: str, is_temporary: bool = False):
        self.status_code = status_code
        self.detail = detail
        self.is_temporary = is_temporary
        super().__init__(f"Zoom API error {status_code}: {detail}")

class ZoomAuthError(Exception):
    pass

@dataclass(frozen=True)
class ZoomMeetingResult:
    meeting_id: str
    join_url: str
    start_url: str
    password: str


class ZoomAPIService:
    TOKEN_URL = "https://zoom.us/oauth/token"
    REVOKE_URL = "https://zoom.us/oauth/revoke"
    API_BASE = "https://api.zoom.us/v2"

    def get_authorization_url(self, state: str) -> str:
        redirect_uri = f"{settings.BACKEND_URL}/api/zoom/oauth/callback"
        return (
            f"https://zoom.us/oauth/authorize"
            f"?response_type=code"
            f"&client_id={settings.ZOOM_CLIENT_ID}"
            f"&redirect_uri={redirect_uri}"
            f"&state={state}"
        )

    def _get_auth_header(self) -> dict:
        auth_str = f"{settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}"
        b64_auth = base64.b64encode(auth_str.encode()).decode()
        return {"Authorization": f"Basic {b64_auth}"}

    async def exchange_code(self, code: str) -> dict:
        redirect_uri = f"{settings.BACKEND_URL}/api/zoom/oauth/callback"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data=data, headers=self._get_auth_header(), timeout=10.0)
        
        if resp.status_code != 200:
            logger.error(f"[zoom_api] exchange_code failed: {resp.status_code} {resp.text}")
            raise ZoomAPIError(resp.status_code, "Failed to exchange authorization code", is_temporary=False)
        return resp.json()

    async def get_user_me(self, access_token: str) -> dict:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self.API_BASE}/users/me",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=10.0
            )
        if resp.status_code != 200:
            logger.error(f"[zoom_api] get_user_me failed: {resp.status_code} {resp.text}")
            raise ZoomAPIError(resp.status_code, "Failed to fetch Zoom user profile", is_temporary=resp.status_code >= 500)
        return resp.json()

    async def _refresh_token(self, token_record: RecruiterZoomToken, db: DBSession) -> str:
        refresh_token = decrypt_zoom_token(token_record.encrypted_refresh_token)
        data = {
            "grant_type": "refresh_token",
            "refresh_token": refresh_token
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.TOKEN_URL, data=data, headers=self._get_auth_header(), timeout=10.0)
            
        if resp.status_code != 200:
            logger.error(f"[zoom_api] refresh_token failed for recruiter {token_record.recruiter_id}: {resp.status_code} {resp.text}")
            if resp.status_code in (400, 401, 403):
                # Permanent failure
                db.delete(token_record)
                db.commit()
                raise ZoomAuthError("Zoom credentials have expired or been revoked. Please reconnect your Zoom account.")
            else:
                # Temporary failure
                raise ZoomAPIError(resp.status_code, "Temporary error refreshing Zoom token", is_temporary=True)
                
        token_data = resp.json()
        new_access_token = token_data["access_token"]
        new_refresh_token = token_data.get("refresh_token", refresh_token)
        expires_in = token_data.get("expires_in", 3600)
        
        token_record.encrypted_access_token = encrypt_zoom_token(new_access_token)
        token_record.encrypted_refresh_token = encrypt_zoom_token(new_refresh_token)
        # Store naive UTC datetime
        token_record.expires_at = datetime.utcnow() + dt.timedelta(seconds=expires_in - 60)
        token_record.last_refresh_at = datetime.utcnow()
        if "scope" in token_data:
            token_record.token_scope = token_data["scope"]
            
        db.commit()
        return new_access_token

    async def get_recruiter_access_token(self, recruiter_id: str, db: DBSession) -> str:
        token_record = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.recruiter_id == recruiter_id).first()
        if not token_record:
            raise ZoomAuthError("Zoom account not connected. Please connect your Zoom account in Settings.")
            
        now = datetime.utcnow()
        if token_record.expires_at < now:
            logger.info(f"[zoom_api] Access token for recruiter {recruiter_id} expired, refreshing...")
            return await self._refresh_token(token_record, db)
            
        return decrypt_zoom_token(token_record.encrypted_access_token)
        
    async def revoke_token(self, access_token: str) -> None:
        data = {"token": access_token}
        async with httpx.AsyncClient() as client:
            resp = await client.post(self.REVOKE_URL, data=data, headers=self._get_auth_header(), timeout=10.0)
        if resp.status_code != 200:
            logger.warning(f"[zoom_api] revoke_token returned {resp.status_code}: {resp.text}")

    async def create_meeting(
        self,
        recruiter_id: str,
        db: DBSession,
        topic: str,
        start_time: str,
        duration_minutes: int = 45,
    ) -> ZoomMeetingResult:
        token = await self.get_recruiter_access_token(recruiter_id, db)

        body = {
            "topic": topic,
            "type": 2,  # Scheduled meeting
            "start_time": start_time,
            "duration": duration_minutes,
            "timezone": "UTC",
            "settings": {
                "join_before_host": False,
                "mute_upon_entry": True,
                "waiting_room": True,
                "auto_recording": "cloud",
            },
        }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self.API_BASE}/users/me/meetings",
                json=body,
                headers={"Authorization": f"Bearer {token}"},
                timeout=15.0,
            )

        if resp.status_code == 401:
            # Token might be revoked on Zoom's side before our DB expires_at, attempt to force refresh once.
            token_record = db.query(RecruiterZoomToken).filter(RecruiterZoomToken.recruiter_id == recruiter_id).first()
            if token_record:
                token = await self._refresh_token(token_record, db)
                async with httpx.AsyncClient() as client:
                    resp = await client.post(
                        f"{self.API_BASE}/users/me/meetings",
                        json=body,
                        headers={"Authorization": f"Bearer {token}"},
                        timeout=15.0,
                    )
                    
        if resp.status_code not in (200, 201):
            logger.error("[zoom_api] create_meeting failed: %s %s", resp.status_code, resp.text)
            raise ZoomAPIError(resp.status_code, f"Failed to create Zoom meeting: {resp.text}", is_temporary=resp.status_code >= 500)

        data = resp.json()
        result = ZoomMeetingResult(
            meeting_id=str(data["id"]),
            join_url=data["join_url"],
            start_url=data["start_url"],
            password=data.get("password", ""),
        )
        logger.info("[zoom_api] meeting created: id=%s by recruiter=%s", result.meeting_id, recruiter_id)
        return result

    async def delete_meeting(self, recruiter_id: str, db: DBSession, meeting_id: str) -> bool:
        """
        Deletes a Zoom meeting. Used for cleanup when a DB commit fails.
        """
        try:
            token = await self.get_recruiter_access_token(recruiter_id, db)
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{self.API_BASE}/meetings/{meeting_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0,
                )
            if resp.status_code in (200, 204):
                logger.info("[zoom_api] orphan meeting %s deleted successfully", meeting_id)
                return True
            else:
                logger.warning(
                    "[zoom_api] failed to delete orphan meeting %s: %s %s",
                    meeting_id, resp.status_code, resp.text,
                )
                return False
        except ZoomAuthError:
            logger.warning("[zoom_api] delete_meeting skipped, recruiter %s not connected to Zoom", recruiter_id)
            return False
        except Exception as e:
            logger.error("[zoom_api] exception deleting orphan meeting %s: %s", meeting_id, e)
            return False

zoom_api = ZoomAPIService()
