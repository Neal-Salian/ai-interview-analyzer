from fastapi import WebSocket
from app.core.security import decode_access_token

active_connections: dict[str, list[WebSocket]]


def verify_ws_token(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    return decode_access_token(token)


async def connect_recruiter(session_id: str, websocket: WebSocket) -> bool:
    payload = verify_ws_token(websocket)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4001)
        print(f"[WS] Rejected unauthenticated connection to session {session_id}")
        return False

    await websocket.accept()
    active_connections[session_id] = websocket
    print(f"[WS] Recruiter {payload['sub']} connected to session {session_id} "
          f"(total active: {len(active_connections)})")
    return True


def disconnect_recruiter(session_id: str):
    active_connections.pop(session_id, None)
    print(f"[WS] Recruiter disconnected from session {session_id} "
          f"(total active: {len(active_connections)})")


async def broadcast(session_id: str, data: dict):
    ws = active_connections.get(session_id)
    if ws:
        try:
            await ws.send_json(data)
        except Exception as e:
            print(f"[WS] Broadcast failed for session {session_id}: {e}")
            disconnect_recruiter(session_id)