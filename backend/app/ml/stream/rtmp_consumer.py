import av
import time
import asyncio
from app.ml.emotion.detector import analyze_frame
from app.ml.speech.transcriber import transcribe_chunk

async def consume_stream(meeting_id: str, rtmp_url: str):
    container = av.open(rtmp_url)

    last_analyzed = 0
    audio_buffer = []

    for packet in container.demux():
        if packet.stream.type == 'video':
            now = time.time()
            if now - last_analyzed >= 1.0:
                frame = packet.decode()[0].to_ndarray(format="bgr24")
                emotion = await asyncio.to_thread(analyze_frame, frame)
                await save_emotion(meeting_id, emotion)
                last_analyzed = now

        elif packet.stream.type == 'audio':
            audio_buffer.append(packet)
            if len(audio_buffer) >= 900:  # ~30 seconds at typical audio packet rate
                transcript = await asyncio.to_thread(transcribe_chunk, audio_buffer)
                await save_transcript(meeting_id, transcript)
                audio_buffer = []