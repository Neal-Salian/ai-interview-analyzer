import av
import time
import asyncio
from app.ml.emotion.detector import analyze_frame
from app.ml.speech.transcriber import transcribe_chunk
from app.db.crud import save_emotion, save_transcript

async def consume_stream(session_id: str, rtmp_url: str):
    container = av.open(rtmp_url, options={"rtmp_live": "live"})

    last_analyzed = 0
    audio_buffer = []
    packet_count = {"video": 0, "audio": 0, "other": 0}

    for packet in container.demux():
        if packet.dts is None:
            continue

        ptype = packet.stream.type
        packet_count[ptype if ptype in packet_count else "other"] += 1

        # Print a summary every 30 packets so you can see what's flowing
        total = sum(packet_count.values())
        if total % 30 == 0:
            print(f"[PACKETS] video={packet_count['video']} audio={packet_count['audio']}")

        if packet.stream.type == 'video':
            now = time.time()
            if now - last_analyzed >= 1.0:
                try:
                    frames = packet.decode()
                    print(f"[VIDEO] decoded {len(frames)} frames from packet")
                    if frames:
                        frame = frames[0].to_ndarray(format="bgr24")
                        print(f"[VIDEO] frame shape: {frame.shape}, running DeepFace...")
                        emotion = await asyncio.to_thread(analyze_frame, frame)
                        print(f"[VIDEO] DeepFace result: {emotion}")
                        await asyncio.to_thread(save_emotion, session_id, emotion)
                        print(f"[EMOTION] saved ✅ {emotion['dominant_emotion']}")
                        last_analyzed = now
                except Exception as e:
                    import traceback
                    print(f"[EMOTION ERROR] {e}")
                    traceback.print_exc()

        elif packet.stream.type == 'audio':
            audio_buffer.append(packet)
            if len(audio_buffer) >= 900:
                try:
                    transcript = await asyncio.to_thread(transcribe_chunk, audio_buffer)
                    await asyncio.to_thread(save_transcript, session_id, transcript)
                    print(f"[TRANSCRIPT] saved ✅ {transcript[:80]}")
                    audio_buffer = []
                except Exception as e:
                    print(f"[TRANSCRIPT ERROR] {e}")
                    audio_buffer = []

    print(f"[DONE] Final packet counts: {packet_count}")