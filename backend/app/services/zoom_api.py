"""
Zoom Server-to-Server OAuth API Service.

Handles:
  - OAuth token acquisition and in-memory caching
  - Meeting creation (used during session scheduling)
  - Meeting deletion (cleanup helper for failed DB commits)

This module does NOT modify any existing Zoom webhook or RTMP logic.
"""
import time
import logging
from dataclasses import dataclass
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Data structures ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class ZoomMeetingResult:
    """Immutable result from a successful Zoom meeting creation."""
    meeting_id: str
    join_url: str
    start_url: str
    password: str


class ZoomAPIError(Exception):
    """Raised when the Zoom API returns a non-2xx response."""
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Zoom API error {status_code}: {detail}")


# ── Service ────────────────────────────────────────────────────────────────────

class ZoomAPIService:
    """
    Server-to-Server OAuth client for the Zoom REST API.

    Token is cached in-memory with a safety margin (60 s before expiry).
    Not thread-safe — suitable for a single-process asyncio server.
    """

    TOKEN_URL = "https://zoom.us/oauth/token"
    API_BASE = "https://api.zoom.us/v2"

    def __init__(self) -> None:
        self._access_token: Optional[str] = None
        self._token_expires_at: float = 0.0  # epoch seconds

    # ── OAuth ──────────────────────────────────────────────────────────────

    async def _get_access_token(self) -> str:
        """
        Returns a valid Server-to-Server OAuth access token.
        Requests a new one if the cached token is expired or missing.
        """
        now = time.time()
        if self._access_token and now < self._token_expires_at:
            return self._access_token

        logger.info("[zoom_api] requesting new Server-to-Server OAuth token")

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                self.TOKEN_URL,
                params={"grant_type": "account_credentials", "account_id": settings.ZOOM_ACCOUNT_ID},
                auth=(settings.ZOOM_CLIENT_ID, settings.ZOOM_CLIENT_SECRET),
                timeout=10.0,
            )

        if resp.status_code != 200:
            logger.error("[zoom_api] token request failed: %s %s", resp.status_code, resp.text)
            raise ZoomAPIError(resp.status_code, "Failed to obtain Zoom access token")

        data = resp.json()
        self._access_token = data["access_token"]
        # Cache with 60-second safety margin
        self._token_expires_at = now + data.get("expires_in", 3600) - 60
        logger.info("[zoom_api] token acquired, expires in %ds", data.get("expires_in", 3600))
        return self._access_token

    # ── Meeting CRUD ───────────────────────────────────────────────────────

    async def create_meeting(
        self,
        topic: str,
        start_time: str,
        duration_minutes: int = 45,
    ) -> ZoomMeetingResult:
        """
        Creates a Zoom meeting via the REST API.

        Args:
            topic: Meeting title (e.g., "Interview — Jane Doe — Software Engineer").
            start_time: ISO 8601 datetime string.
            duration_minutes: Expected duration (default 45).

        Returns:
            ZoomMeetingResult with meeting_id, join_url, start_url, password.

        Raises:
            ZoomAPIError on any non-2xx response.
        """
        token = await self._get_access_token()

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

        if resp.status_code not in (200, 201):
            logger.error("[zoom_api] create_meeting failed: %s %s", resp.status_code, resp.text)
            raise ZoomAPIError(resp.status_code, f"Failed to create Zoom meeting: {resp.text}")

        data = resp.json()
        result = ZoomMeetingResult(
            meeting_id=str(data["id"]),
            join_url=data["join_url"],
            start_url=data["start_url"],
            password=data.get("password", ""),
        )
        logger.info("[zoom_api] meeting created: id=%s", result.meeting_id)
        return result

    async def delete_meeting(self, meeting_id: str) -> bool:
        """
        Deletes a Zoom meeting.  Used only for cleanup when a DB commit
        fails after a meeting was already created.

        Returns True if deletion succeeded, False otherwise.
        Never raises — errors are logged and swallowed.
        """
        try:
            token = await self._get_access_token()
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
        except Exception as e:
            logger.error("[zoom_api] exception deleting orphan meeting %s: %s", meeting_id, e)
            return False


# ── Module-level singleton ─────────────────────────────────────────────────────

zoom_api = ZoomAPIService()
