from fastapi import WebSocket


active_connections: dict[str, WebSocket] = {}

async def connect_recruiter(meeting_id: str, websocket: WebSocket):
    await websocket.accept()
    active_connections[meeting_id] = websocket

async def broadcast(meeting_id: str, data: dict):
    ws = active_connections.get(meeting_id)
    if ws:
        await ws.send_json(data)