"""
WebSocket broadcast test.
Confirms that:
  1. A client can connect to /ws/live/{session_id}
  2. History is replayed immediately on connect
  3. Live emotion broadcasts arrive in real time
  4. Reconnect gets full history again

Run from backend/ with dev-backend running in another terminal:
    PYTHONPATH=. python tests/test_websocket.py
"""

import asyncio
import uuid
import datetime
import sys
import json
import websockets

from app.db.database import SessionLocal
from app.db.models import Candidate, Session as InterviewSession
from app.db.crud import save_emotion, save_transcript
from app.api.websocket import broadcast

BASE_WS_URL = "ws://localhost:8001/ws/live"


def setup_test_session_with_history() -> str:
    db = SessionLocal()
    try:
        candidate = Candidate(
            id=uuid.uuid4(),
            name="WebSocket Test Candidate",
            email=f"wstest_{uuid.uuid4().hex[:6]}@test.com",
            created_at=datetime.datetime.utcnow()
        )
        db.add(candidate)
        db.flush()

        session = InterviewSession(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            zoom_meeting_id="ws-test-001",
            status="active",
            started_at=datetime.datetime.utcnow()
        )
        db.add(session)
        db.commit()
        session_id = str(session.id)

        # Pre-populate with history so replay test has data
        save_emotion(session_id, {
            "dominant_emotion": "neutral",
            "confidence": 72.5
        })
        save_emotion(session_id, {
            "dominant_emotion": "happy",
            "confidence": 88.3
        })
        save_transcript(
            session_id,
            "I have led teams of up to 10 engineers."
        )

        print(f"[SETUP] Session: {session_id}")
        print(f"[SETUP] Pre-populated: 2 emotions, 1 transcript")
        return session_id
    finally:
        db.close()


async def recv_with_timeout(ws, timeout=8.0):
    raw = await asyncio.wait_for(ws.recv(), timeout=timeout)
    return json.loads(raw)


async def test_history_replay(session_id: str) -> bool:
    print(f"\n[TEST 1] History replay on connect...")
    url = f"{BASE_WS_URL}/{session_id}"

    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            msg = await recv_with_timeout(ws)

            if msg.get("type") != "history":
                print(f"  ❌ FAIL: expected 'history', got '{msg.get('type')}'")
                return False

            emotions = msg.get("emotions", [])
            transcripts = msg.get("transcripts", [])
            print(f"  Received: {len(emotions)} emotions, {len(transcripts)} transcripts")

            if len(emotions) != 2:
                print(f"  ❌ FAIL: expected 2 emotions, got {len(emotions)}")
                return False

            if len(transcripts) != 1:
                print(f"  ❌ FAIL: expected 1 transcript, got {len(transcripts)}")
                return False

            print(f"  ✅ PASS: history replayed correctly")
            return True

    except asyncio.TimeoutError:
        print(f"  ❌ FAIL: timed out waiting for history message")
        return False


async def test_live_broadcast(session_id: str) -> bool:
    print(f"\n[TEST 2] Live broadcast...")
    url = f"{BASE_WS_URL}/{session_id}"

    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            # Drain history first
            await recv_with_timeout(ws)

            # Push a broadcast directly into the WebSocket layer
            await broadcast(session_id, {
                "type": "emotion",
                "dominant_emotion": "surprised",
                "confidence": 91.2
            })

            msg = await recv_with_timeout(ws)

            if msg.get("type") != "emotion":
                print(f"  ❌ FAIL: expected 'emotion', got '{msg.get('type')}'")
                return False

            if msg.get("dominant_emotion") != "surprised":
                print(f"  ❌ FAIL: wrong emotion '{msg.get('dominant_emotion')}'")
                return False

            print(f"  ✅ PASS: live broadcast received — "
                  f"{msg['dominant_emotion']} ({msg['confidence']}%)")
            return True

    except asyncio.TimeoutError:
        print(f"  ❌ FAIL: timed out waiting for broadcast")
        return False


async def test_reconnect_gets_history(session_id: str) -> bool:
    print(f"\n[TEST 3] Reconnect gets full history...")
    url = f"{BASE_WS_URL}/{session_id}"

    # First connection — drain and disconnect
    async with websockets.connect(url, open_timeout=10) as ws:
        await recv_with_timeout(ws)
        print(f"  First connection: history received, disconnecting...")

    await asyncio.sleep(1)

    # Reconnect — must get history again
    try:
        async with websockets.connect(url, open_timeout=10) as ws:
            msg = await recv_with_timeout(ws)

            if msg.get("type") != "history":
                print(f"  ❌ FAIL: reconnect got '{msg.get('type')}' not 'history'")
                return False

            print(f"  ✅ PASS: reconnect replayed history correctly")
            return True

    except asyncio.TimeoutError:
        print(f"  ❌ FAIL: timed out on reconnect")
        return False


async def main():
    session_id = setup_test_session_with_history()

    results = []
    results.append(await test_history_replay(session_id))
    results.append(await test_live_broadcast(session_id))
    results.append(await test_reconnect_gets_history(session_id))

    print(f"\n{'='*55}")
    passed = sum(results)
    total = len(results)
    print(f"[RESULTS] {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All WebSocket tests passed!\n")
    else:
        print("❌ Some tests failed\n")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())