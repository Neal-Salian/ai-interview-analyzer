from fastapi import WebSocket

# Holds one active WebSocket per session_id
# When a recruiter reconnects, the old entry is simply overwritten
active_connections: dict[str, WebSocket] = {}


async def connect_recruiter(session_id: str, websocket: WebSocket):
    await websocket.accept()
    active_connections[session_id] = websocket
    print(f"[WS] Recruiter connected to session {session_id} "
          f"(total active: {len(active_connections)})")


def disconnect_recruiter(session_id: str):
    active_connections.pop(session_id, None)
    print(f"[WS] Recruiter disconnected from session {session_id} "
          f"(total active: {len(active_connections)})")


async def broadcast(session_id: str, data: dict):
    """
    Sends data to the recruiter watching this session.
    If the send fails (recruiter disconnected), cleans up
    the stale connection so it doesn't block future broadcasts.
    """
    ws = active_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(data)
        except Exception as e:
            print(f"[WS] Broadcast failed for session {session_id}: {e}")
            disconnect_recruiter(session_id)