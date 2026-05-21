from fastapi import APIRouter, Request, BackgroundTasks
import hmac, hashlib, asyncio

router = APIRouter()

@router.post("/webhook/zoom")
async def zoom_webhook(request: Request, background_tasks: BackgroundTasks):
    body = await request.json()
    event = body.get("event")

    if event == "endpoint.url_validation":
        token = body["payload"]["plainToken"]
        hash_val = hmac.new(
            ZOOM_WEBHOOK_SECRET.encode(),
            token.encode(),
            hashlib.sha256
        ).hexdigest()
        return {"plainToken": token, "encryptedToken": hash_val}

    if event == "meeting.started":
        meeting_id = body["payload"]["object"]["id"]
        background_tasks.add_task(
            consume_stream,
            meeting_id,
            f"rtmp://localhost/live/{meeting_id}"
        )
        return {"status": "stream started"}

    if event == "meeting.ended":
        return {"status": "meeting ended"}