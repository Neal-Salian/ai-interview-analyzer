import av
import time
import asyncio
from app.ml.emotion.detector import analyze_frame
from app.ml.speech.transcriber import transcribe_chunk
from app.db.crud import save_emotion, save_transcript
from app.api.websocket import broadcast


async def consume_stream(session_id: str, rtmp_url: str):
    print(f"[CONSUMER] Opening stream: {rtmp_url}")

    try:
        container = av.open(rtmp_url, options={"rtmp_live": "live"})
    except Exception as e:
        print(f"[CONSUMER] Failed to open stream: {e}")
        return

    last_analyzed = 0
    audio_buffer = []

    print(f"[CONSUMER] Stream opened. Starting packet loop...")

    for packet in container.demux():
        if packet.dts is None:
            continue

        if packet.stream.type == 'video':
            now = time.time()
            if now - last_analyzed >= 1.0:
                try:
                    frames = packet.decode()
                    if not frames:
                        continue

                    frame = frames[0].to_ndarray(format="bgr24")
                    emotion = await asyncio.to_thread(analyze_frame, frame)

                    # Save to DB
                    await asyncio.to_thread(save_emotion, session_id, emotion)

                    # Broadcast to dashboard over WebSocket
                    await broadcast(session_id, {
                        "type": "emotion",
                        "dominant_emotion": emotion["dominant_emotion"],
                        "confidence": emotion["confidence"],
                    })

                    print(f"[EMOTION] {emotion['dominant_emotion']} ({emotion['confidence']:.1f}%)")
                    last_analyzed = now

                except Exception as e:
                    print(f"[EMOTION ERROR] {e}")

        elif packet.stream.type == 'audio':
            audio_buffer.append(packet)

            if len(audio_buffer) >= 900:
                try:
                    transcript = await asyncio.to_thread(
                        transcribe_chunk, audio_buffer
                    )

                    # Save to DB
                    await asyncio.to_thread(save_transcript, session_id, transcript)

                    # Broadcast to dashboard over WebSocket
                    await broadcast(session_id, {
                        "type": "transcript",
                        "text": transcript,
                    })

                    print(f"[TRANSCRIPT] {transcript[:80]}")
                    audio_buffer = []

                except Exception as e:
                    print(f"[TRANSCRIPT ERROR] {e}")
                    audio_buffer = []

    print(f"[CONSUMER] Stream ended for session {session_id}")