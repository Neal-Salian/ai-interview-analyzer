import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import zoom_webhook, jobs, sessions
from app.api.websocket import connect_recruiter, disconnect_recruiter
from app.db.crud import get_active_sessions, get_session_history
from app.ml.stream.rtmp_consumer import consume_stream


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        active = get_active_sessions()
        for session in active:
            if session.zoom_meeting_id:
                rtmp_url = f"rtmp://localhost:1935/live/{session.zoom_meeting_id}"
                print(f"[STARTUP] Recovering consumer for session {session.id}")
                asyncio.create_task(consume_stream(str(session.id), rtmp_url))
        print(f"[STARTUP] Recovery check done — {len(active)} active session(s) found")
    except Exception as e:
        # DB might not be ready yet — log and continue, don't crash the server
        print(f"[STARTUP] Could not check active sessions (DB unavailable?): {e}")
    yield


app = FastAPI(title="AI Interview Analyzer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(zoom_webhook.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(sessions.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/ws/live/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connect_recruiter(session_id, websocket)
    try:
        history = await asyncio.to_thread(get_session_history, session_id)
        if history["emotions"] or history["transcripts"]:
            await websocket.send_json({
                "type": "history",
                "emotions": history["emotions"],
                "transcripts": history["transcripts"]
            })
            print(f"[WS] Replayed {len(history['emotions'])} emotions, "
                  f"{len(history['transcripts'])} transcripts to session {session_id}")

        # Keep connection alive — frontend doesn't send messages
        # so we just keep the loop open until disconnect
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send a ping every 30s to keep the connection alive
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        disconnect_recruiter(session_id)
    except Exception:
        disconnect_recruiter(session_id)