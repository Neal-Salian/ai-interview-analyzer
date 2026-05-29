import av
import time
import asyncio
import logging
from app.ml.emotion.detector import analyze_frame
from app.ml.speech.transcriber import transcribe_chunk
from app.ml.llm.question_generator import generate_analysis
from app.db.crud import save_emotion, save_transcript, save_question
from app.api.websocket import broadcast

logger = logging.getLogger(__name__)

# How many transcript chunks to skip between LLM calls.
# 0 = call after every chunk (good for testing)
# 2 = call every 3rd chunk (lighter on CPU during long interviews)
LLM_EVERY_N_CHUNKS = 0

async def consume_stream(session_id: str, rtmp_url: str):
    logger.info(f"[CONSUMER] Opening stream: {rtmp_url}")

    try:
        container = av.open(rtmp_url, options={"rtmp_live": "live"})
    except Exception as e:
        logger.error(f"[CONSUMER] Failed to open stream: {e}")
        return

    last_analyzed = 0
    audio_buffer = []
    transcript_chunk_count = 0

    logger.info("[CONSUMER] Stream opened. Starting packet loop...")

    for packet in container.demux():
        if packet.dts is None:
            continue

        # ── Video — emotion detection at 1fps ─────────────────────────────────
        if packet.stream.type == 'video':
            now = time.time()
            if now - last_analyzed >= 1.0:
                try:
                    frames = packet.decode()
                    if not frames:
                        continue

                    frame = frames[0].to_ndarray(format="bgr24")
                    emotion = await asyncio.to_thread(analyze_frame, frame)

                    await asyncio.to_thread(save_emotion, session_id, emotion)

                    await broadcast(session_id, {
                        "type": "emotion",
                        "dominant_emotion": emotion["dominant_emotion"],
                        "confidence": emotion["confidence"],
                    })

                    logger.debug(
                        f"[EMOTION] {emotion['dominant_emotion']} "
                        f"({emotion['confidence']:.1f}%)"
                    )
                    last_analyzed = now

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"[EMOTION ERROR] {e}")

        # ── Audio — transcription + question generation ───────────────────────
        elif packet.stream.type == 'audio':
            audio_buffer.append(packet)

            if len(audio_buffer) >= 900:
                try:
                    transcript = await asyncio.to_thread(
                        transcribe_chunk, audio_buffer
                    )
                    audio_buffer = []
                    transcript_chunk_count += 1

                    # Save transcript to DB
                    await asyncio.to_thread(save_transcript, session_id, transcript)

                    # Broadcast transcript to dashboard
                    await broadcast(session_id, {
                        "type": "transcript",
                        "text": transcript,
                    })

                    logger.info(f"[TRANSCRIPT] {transcript[:80]}")

                    # ── LLM question generation ───────────────────────────────
                    # Fire-and-forget so it never blocks the audio loop
                    if transcript_chunk_count % (LLM_EVERY_N_CHUNKS + 1) == 0:
                        asyncio.create_task(
                            _generate_and_broadcast_questions(
                                session_id=session_id,
                                transcript=transcript,
                                job_id="",  # wire to session.job_id when candidates route is built
                            )
                        )

                except asyncio.CancelledError:
                    raise
                except Exception as e:
                    logger.warning(f"[TRANSCRIPT ERROR] {e}")
                    audio_buffer = []

    logger.info(f"[CONSUMER] Stream ended for session {session_id}")


async def _generate_and_broadcast_questions(
    session_id: str,
    transcript: str,
    job_id: str,
) -> None:
    """
    Runs LLM analysis on a transcript chunk, saves questions to DB,
    and broadcasts each question card over WebSocket.
    Runs as a background task — never blocks the main consumer loop.
    """
    try:
        result = await generate_analysis(transcript, job_id)
        if not result:
            return

        questions_to_save = []

        # Pressure question
        if result.get("pressure_question"):
            questions_to_save.append({
                "text": result["pressure_question"],
                "triggered_by": "pressure"
            })

        # Lifeline question
        if result.get("lifeline_question"):
            questions_to_save.append({
                "text": result["lifeline_question"],
                "triggered_by": "lifeline"
            })

        for q in questions_to_save:
            question_id = await asyncio.to_thread(
                save_question,
                session_id,
                q["text"],
                q["triggered_by"],
            )

            # Broadcast each question as it's saved
            await broadcast(session_id, {
                "type": "question",
                "question": {
                    "id": question_id,
                    "question_text": q["text"],
                    "triggered_by": q["triggered_by"],
                    "was_asked": False,
                    "created_at": "",
                }
            })

            logger.info(f"[QUESTION] [{q['triggered_by']}] {q['text'][:60]}")

        # Log STAR feedback and confidence score but don't broadcast
        # — these will be used in the session report
        if result.get("star_feedback"):
            logger.info(f"[STAR] {result['star_feedback']}")
        if result.get("confidence_score"):
            logger.info(f"[CONFIDENCE] {result['confidence_score']}/10")

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(f"[LLM ERROR] question generation failed: {e}")