import abc
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class MeetingResult:
    meeting_id: str
    join_url: str
    start_url: str
    password: str

class ProviderError(Exception):
    """Base exception for all provider errors."""
    pass

class ProviderAuthError(ProviderError):
    """Raised when the provider authentication fails (e.g., token expired/missing)."""
    pass

class MeetingProvider(abc.ABC):
    @abc.abstractmethod
    async def create_meeting(self, **kwargs) -> MeetingResult:
        """Create a new meeting and return the connection details."""
        pass

class ZoomMeetingProvider(MeetingProvider):
    async def create_meeting(self, **kwargs) -> MeetingResult:
        from app.services.zoom_api import zoom_api, ZoomAuthError, ZoomAPIError
        
        try:
            zoom_result = await zoom_api.create_meeting(**kwargs)
            return MeetingResult(
                meeting_id=zoom_result.meeting_id,
                join_url=zoom_result.join_url,
                start_url=zoom_result.start_url,
                password=zoom_result.password,
            )
        except ZoomAuthError as e:
            raise ProviderAuthError(str(e))
        except ZoomAPIError as e:
            raise ProviderError(str(e))
        except Exception as e:
            raise ProviderError(f"Unexpected Zoom error: {str(e)}")

class MockMeetingProvider(MeetingProvider):
    async def create_meeting(self, **kwargs) -> MeetingResult:
        """
        Creates a mock meeting suitable for OBS RTMP ingestion.
        """
        mock_id = f"mock-obs-{uuid.uuid4().hex[:8]}"
        return MeetingResult(
            meeting_id=mock_id,
            join_url=f"http://localhost:5173/mock-join/{mock_id}",
            start_url=f"http://localhost:5173/mock-start/{mock_id}",
            password="",
        )

def get_meeting_provider(provider_type: str = "zoom") -> MeetingProvider:
    if provider_type == "mock":
        return MockMeetingProvider()
    return ZoomMeetingProvider()
