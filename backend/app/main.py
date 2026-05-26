from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes import zoom_webhook, jobs, sessions
from app.api.websocket import connect_recruiter, disconnect_recruiter

app = FastAPI(title="AI Interview Analyzer")

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
        # Keep connection alive — just listen for any client messages
        # (client doesn't send anything, but we need to keep the loop open)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect_recruiter(session_id)