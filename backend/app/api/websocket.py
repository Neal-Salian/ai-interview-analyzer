import logging
import asyncio
from fastapi import WebSocket
from app.core.security import decode_access_token

logger = logging.getLogger(__name__)

# Note: This implementation supports multiple recruiters within a single 
# application process only. Cross-worker WebSocket broadcasting will 
# require a shared backplane (e.g., Redis Pub/Sub).
active_connections: dict[str, list[WebSocket]] = {}


def verify_ws_token(websocket: WebSocket) -> dict | None:
    token = websocket.query_params.get("token")
    if not token:
        return None
    return decode_access_token(token)


async def connect_recruiter(session_id: str, websocket: WebSocket) -> bool:
    payload = verify_ws_token(websocket)
    if not payload or not payload.get("sub"):
        await websocket.close(code=4001)
        logger.warning(f"[WS] Rejected unauthenticated connection to session {session_id}")
        return False

    if session_id not in active_connections:
        active_connections[session_id] = []
        
    if websocket not in active_connections[session_id]:
        active_connections[session_id].append(websocket)

    logger.info(f"[WS] Recruiter {payload['sub']} connected to session {session_id} "
                f"(session connections: {len(active_connections[session_id])}, "
                f"total active sessions: {len(active_connections)})")
    return True


def disconnect_recruiter(session_id: str, websocket: WebSocket):
    if session_id in active_connections:
        if websocket in active_connections[session_id]:
            active_connections[session_id].remove(websocket)
            logger.info(f"[WS] Recruiter disconnected from session {session_id} "
                        f"(session connections: {len(active_connections[session_id])}, "
                        f"total active sessions: {len(active_connections)})")
        
        if not active_connections[session_id]:
            del active_connections[session_id]
            logger.info(f"[WS] Session {session_id} has no more connections, cleaned up state.")


async def broadcast(session_id: str, data: dict):
    if session_id in active_connections:
        # Iterate over a copy of the list to allow safe removal during iteration
        for ws in list(active_connections[session_id]):
            try:
                # Add a reasonable timeout around send_json to protect against stalled clients
                await asyncio.wait_for(ws.send_json(data), timeout=2.0)
            except Exception as e:
                logger.warning(f"[WS] Broadcast failed for session {session_id}, removing connection. Error: {e}")
                disconnect_recruiter(session_id, ws)