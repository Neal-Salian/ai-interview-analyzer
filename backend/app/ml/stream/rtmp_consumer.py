import av
import asyncio
from app.ml.emotion.detector import analyze_frame
from app.ml.speech.transciber imoprt transcribe_chunk

async def consume_stream(meeting_id: str, rtmp_url: str):
    container = av.open(rtmp_url)

    frame_count = 0
    audio_buffer = []

    for packet in container.demux():
        if packet.stream.type == 'video':
            if frame_count % 5 == 0:
                frame = packet.decode()[0].to_ndarray(format="bgr24")
                emotion = analyze_frame(frame)
                await save_emotion(meeting_id, emotion)
            frame_count += 1
        
        if packet.stream.type == 'audio':
            audio_buffer.append(packet)
            if len(audio_buffer) >= 30:
                transcript =transcribe_chunk(audio_buffer)
                await save_transcript(meeting_id, transcript)
                audio_buffer = []                
                