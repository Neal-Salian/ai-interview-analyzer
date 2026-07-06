import pytest
import uuid
import datetime
from app.core.providers import (
    get_meeting_provider,
    ZoomMeetingProvider,
    MockMeetingProvider,
    MeetingResult
)
from app.db.models import Session
from app.db.database import Base

def test_provider_factory():
    zoom_provider = get_meeting_provider("zoom")
    assert isinstance(zoom_provider, ZoomMeetingProvider)
    
    mock_provider = get_meeting_provider("mock")
    assert isinstance(mock_provider, MockMeetingProvider)

@pytest.mark.anyio
async def test_mock_provider():
    provider = get_meeting_provider("mock")
    result = await provider.create_meeting(
        recruiter_id="test_recruiter",
        db=None,
        topic="Test Topic",
        start_time=datetime.datetime.utcnow().isoformat() + "Z",
        duration_minutes=45
    )
    
    assert isinstance(result, MeetingResult)
    assert result.meeting_id.startswith("mock-obs-")
    assert "mock-join" in result.join_url
    assert "mock-start" in result.start_url
    assert result.password == ""

def test_db_translation():
    # Simulate the translation layer in schedule_session
    mock_result = MeetingResult(
        meeting_id="mock-obs-123",
        join_url="http://localhost/join",
        start_url="http://localhost/start",
        password=""
    )
    
    session = Session(id=uuid.uuid4())
    
    # Translation layer logic
    session.zoom_meeting_id = mock_result.meeting_id
    session.zoom_join_url = mock_result.join_url
    session.zoom_start_url = mock_result.start_url
    session.zoom_password = mock_result.password
    session.meeting_provider = "mock"
    
    # Assert
    assert session.zoom_meeting_id == "mock-obs-123"
    assert session.zoom_join_url == "http://localhost/join"
    assert session.meeting_provider == "mock"
