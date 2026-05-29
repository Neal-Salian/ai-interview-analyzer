"""
Direct pipeline test — bypasses RTMP/nginx and tests DeepFace + DB directly.
Proves the ML→DB pipeline works without nginx being in the way.

Run from backend/:
    PYTHONPATH=. python tests/test_stream.py
"""

import asyncio
import uuid
import datetime
import sys
import numpy as np
import cv2

from app.db.database import SessionLocal
from app.db.models import Candidate, Session as InterviewSession, EmotionFrame, TranscriptChunk
from app.db.crud import save_emotion, save_transcript
from app.ml.emotion.detector import analyze_frame


def setup_test_session() -> str:
    db = SessionLocal()
    try:
        candidate = Candidate(
            id=uuid.uuid4(),
            name="Pipeline Test Candidate",
            email=f"test_{uuid.uuid4().hex[:6]}@pipeline.test",
            created_at=datetime.datetime.utcnow()
        )
        db.add(candidate)
        db.flush()

        session = InterviewSession(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            zoom_meeting_id="pipeline-test-001",
            status="active",
            started_at=datetime.datetime.utcnow()
        )
        db.add(session)
        db.commit()
        session_id = str(session.id)
        print(f"[SETUP] Created session: {session_id}")
        return session_id
    finally:
        db.close()


def make_test_frame() -> np.ndarray:
    """Generate a synthetic BGR frame with a face-like region DeepFace can process."""
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    # Draw a skin-toned ellipse as a stand-in face
    cv2.ellipse(frame, (320, 240), (100, 130), 0, 0, 360, (180, 140, 100), -1)
    # Eyes
    cv2.circle(frame, (280, 210), 15, (50, 30, 20), -1)
    cv2.circle(frame, (360, 210), 15, (50, 30, 20), -1)
    # Mouth
    cv2.ellipse(frame, (320, 290), (40, 20), 0, 0, 180, (100, 60, 60), -1)
    return frame


async def test_emotion_pipeline(session_id: str, num_frames: int = 3):
    print(f"\n[TEST] Running emotion pipeline with {num_frames} synthetic frames...")
    frame = make_test_frame()

    for i in range(num_frames):
        try:
            emotion = await asyncio.to_thread(analyze_frame, frame)
            await asyncio.to_thread(save_emotion, session_id, emotion)
            print(f"  Frame {i+1}: {emotion['dominant_emotion']} ({emotion['confidence']:.1f}%) ✅")
        except Exception as e:
            print(f"  Frame {i+1}: ERROR — {e}")
            import traceback; traceback.print_exc()


async def test_transcript_pipeline(session_id: str):
    print(f"\n[TEST] Running transcript pipeline...")
    try:
        # Save a fake transcript chunk directly (Whisper tested separately)
        await asyncio.to_thread(
            save_transcript,
            session_id,
            "I have five years of experience in Python and have led multiple backend projects."
        )
        print("  Transcript chunk saved ✅")
    except Exception as e:
        print(f"  ERROR — {e}")
        import traceback; traceback.print_exc()


def check_results(session_id: str):
    db = SessionLocal()
    try:
        emotions = db.query(EmotionFrame).filter(
            EmotionFrame.session_id == session_id
        ).all()
        transcripts = db.query(TranscriptChunk).filter(
            TranscriptChunk.session_id == session_id
        ).all()

        print(f"\n{'='*55}")
        print(f"[RESULTS] emotion_frames    : {len(emotions)} rows")
        for e in emotions:
            print(f"          {e.dominant_emotion} ({e.confidence:.1f}%) @ {e.timestamp}")

        print(f"[RESULTS] transcript_chunks : {len(transcripts)} rows")
        for t in transcripts:
            print(f"          '{t.text[:70]}'")
        print(f"{'='*55}")

        passed = True
        if len(emotions) == 0:
            print("❌ FAIL: No emotion frames in DB")
            passed = False
        else:
            print(f"✅ PASS: {len(emotions)} emotion frames written")

        if len(transcripts) == 0:
            print("❌ FAIL: No transcript chunks in DB")
            passed = False
        else:
            print(f"✅ PASS: {len(transcripts)} transcript chunks written")

        if not passed:
            sys.exit(1)

    finally:
        db.close()


async def main():
    session_id = setup_test_session()
    await test_emotion_pipeline(session_id, num_frames=3)
    await test_transcript_pipeline(session_id)
    check_results(session_id)
    print("\n🎉 Full pipeline test complete — DB writes confirmed.\n")


if __name__ == "__main__":
    asyncio.run(main())