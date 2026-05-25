import uuid
import datetime
from app.db.database import SessionLocal
from app.db.models import EmotionFrame, TranscriptChunk

def save_emotion(session_id: str, emotion: dict):
    db = SessionLocal()
    try:
        frame = EmotionFrame(
            id=uuid.uuid4(),
            session_id=session_id,
            dominant_emotion=emotion["dominant_emotion"],
            confidence=emotion["confidence"],
            timestamp=datetime.datetime.utcnow()
        )
        db.add(frame)
        db.commit()
    finally:
        db.close()



def save_transcript(session_id: str, text: str):
    db = SessionLocal()
    try:
        chunk = TranscriptChunk(
            id=uuid.uuid4(),
            session_id=session_id,
            text=text,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(chunk)
        db.commit()
    finally:
        db.close()