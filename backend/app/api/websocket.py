from fastapi import WebSocket, WebSocketDisconnect
import asyncio


active_connections: dict[str, WebSocket] = {}

async def connect_recruiter(session_id: str, websocket: WebSocket):
    await websocket.accept()
    active_connections[session_id]=websocket
    print(f"[WS] Recruiter connected to session {session_id}")


def disconnect_recruiter(session_id: str):
    active_connections.pop(session_id, None)
    print(f"[WS] Recruiter disconnected from session {session_id}")


async def broadcast(session_id: str, data: dict):
    ws = active_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(data)
        except Exception as e:
            print(f"[WS] Broadcast error for session {session_id}: {e}")
            disconnect_recruiter(session_id)
            