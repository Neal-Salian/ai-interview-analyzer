import av
import time
import asyncio
import logging
from app.ml.emotion.detector import analyze_frame
from app.ml.vision.attention_analyzer import analyze_attention
from app.ml.speech.transcriber import transcribe_chunk
from app.ml.llm.question_generator import generate_analysis
from app.ml.nlp.scorer import score_sentiment
from app.db.crud import (
    save_emotion, save_transcript, save_question,
    save_attention, save_integrity_event,
)
from app.api.websocket import broadcast
from app.core.logging_config import log_event
from app.runtime.manager import RuntimeManager
from app.ml.tracking.candidate_tracker import (
    TrackingStatus, enroll_from_frames, verify_candidate,
    crop_candidate, create_tracker, init_tracker, update_tracker,
    ENROLLMENT_FRAMES_TARGET, STABILISATION_FRAMES, VERIFY_COOLDOWN_FRAMES,
    _ensure_deepface_model,
)

logger = logging.getLogger(__name__)

# How many transcript chunks to skip between LLM calls.
# 0 = call after every chunk (good for testing)
# 2 = call every 3rd chunk (lighter on CPU during long interviews)
LLM_EVERY_N_CHUNKS = 0


async def consume_stream(session_id: str, rtmp_url: str, job_id: str = ""):
    logger.info(f"[CONSUMER] Opening stream: {rtmp_url}")

    container = None
    try:
        container = await asyncio.to_thread(
            av.open, rtmp_url, timeout=5.0
        )
    except Exception as e:
        logger.exception(f"[CONSUMER] Failed to open stream: {e}")
        log_event(logger, "consumer_failed", level=logging.ERROR,
                  session_id=session_id, error_type=type(e).__name__,
                  error_message=str(e))
        return

    # Pre-load DeepFace model once for the session
    try:
        await asyncio.to_thread(_ensure_deepface_model)
    except Exception as e:
        logger.warning(f"[CONSUMER] DeepFace pre-load failed (non-fatal): {e}")

    try:

        last_analyzed = 0
        audio_buffer = []
        transcript_chunk_count = 0
        integrity_state = {}  # Phase 3: persistent state for liveness tracking


        # ── Candidate tracking state (local to consumer) ─────────────
        enrollment_buffer = []       # Captured frames during enrollment
        cv_tracker = None            # OpenCV tracker instance (owned here)
        last_tracking_status = None  # For state-change WebSocket emits

        logger.info("[CONSUMER] Stream opened. Starting packet loop...")
        log_event(logger, "consumer_started",
                  session_id=session_id, rtmp_url=rtmp_url)

        demuxer = container.demux()
        while True:
            try:
                # Wrap the synchronous blocking read in a thread
                receive_ts = time.time()
                packet = await asyncio.to_thread(lambda d: next(d, None), demuxer)
                if packet is None:
                    raise ConnectionError("Stream reached unexpected EOF (network drop?)")
                read_duration = time.time() - receive_ts
                logger.info(f"[TIMING] packet receive took {read_duration*1000:.1f}ms")
            except StopIteration:
                raise ConnectionError("Stream reached unexpected StopIteration (network drop?)")
            except Exception as e:
                logger.warning(f"[CONSUMER] stream read error or timeout for {session_id}: {e}")
                raise ConnectionError(f"Stream read error: {e}") from e

            if packet.dts is None:
                continue

            # ── Video — emotion + attention at 1fps ───────────────────────────────
            if packet.stream.type == 'video':
                now = time.time()
                if now - last_analyzed >= 1.0:
                    try:
                        decode_start = time.time()
                        frames = await asyncio.to_thread(packet.decode)
                        logger.info(f"[TIMING] video decode took {(time.time() - decode_start)*1000:.1f}ms")
                        if not frames:
                            continue

                        frame = frames[0].to_ndarray(format="bgr24")
                        tracking_meta = RuntimeManager.get_tracking_metadata(session_id)
                        tracking_status = tracking_meta.get("tracking_status", TrackingStatus.NOT_ENROLLED) if tracking_meta else TrackingStatus.NOT_ENROLLED

                        # ── Enrollment capture ────────────────────────────
                        if tracking_status == TrackingStatus.ENROLLING:
                            logger.info(f"[ENROLLMENT DEBUG 1] Enrollment requested. Buffer size before append: {len(enrollment_buffer)}")
                            enrollment_buffer.append(frame.copy())

                            if len(enrollment_buffer) >= ENROLLMENT_FRAMES_TARGET:
                                logger.info(f"[ENROLLMENT DEBUG 2] Number of buffered frames: {len(enrollment_buffer)}")
                                # Perform atomic enrollment
                                result = await asyncio.to_thread(
                                    enroll_from_frames, enrollment_buffer
                                )
                                enrollment_buffer = []

                                logger.info(f"[ENROLLMENT DEBUG 8] TrackingStatus before update: {tracking_status.value if hasattr(tracking_status, 'value') else tracking_status}")

                                if result.success:
                                    from app.core.config import settings
                                    RuntimeManager.update_tracking_metadata(
                                        session_id,
                                        tracking_status=TrackingStatus.TRACKING,
                                        candidate_embedding=result.embedding,
                                        last_known_bbox=result.bbox,
                                        confidence=1.0,
                                        last_verified_timestamp=now,
                                        stabilisation_frames_remaining=STABILISATION_FRAMES,
                                        tracking_acquired_at=now,
                                        enrollment_error=None,
                                    )
                                    logger.info(f"[ENROLLMENT DEBUG 10] Database (Redis) update result for success: SUCCESS")
                                    # Initialize OpenCV tracker
                                    cv_tracker = create_tracker()
                                    init_tracker(cv_tracker, frame, result.bbox)
                                    log_event(logger, "tracking_acquired",
                                              session_id=session_id)
                                else:
                                    RuntimeManager.update_tracking_metadata(
                                        session_id,
                                        tracking_status=TrackingStatus.NOT_ENROLLED,
                                        enrollment_start_time=None,
                                        enrollment_error=result.reason,
                                    )
                                    logger.info(f"[ENROLLMENT DEBUG 10] Database (Redis) update result for failure: SUCCESS")
                                    log_event(logger, "enrollment_failed",
                                              session_id=session_id, reason=result.reason)

                                post_update_meta = RuntimeManager.get_tracking_metadata(session_id)
                                post_ts = post_update_meta.get("tracking_status")
                                logger.info(f"[ENROLLMENT DEBUG 9] TrackingStatus after update: {post_ts.value if hasattr(post_ts, 'value') else post_ts}")

                            last_analyzed = now
                            continue  # Skip analysis during enrollment

                        # ── Determine analysis frame ──────────────────────
                        # Default: full frame (V1 backwards-compatible behavior)
                        analysis_frame = frame
                        candidate_identified = False

                        if tracking_status == TrackingStatus.TRACKING:
                            # Stabilisation delay: skip analysis for first N frames
                            stab = tracking_meta.get("stabilisation_frames_remaining", 0)
                            if stab > 0:
                                RuntimeManager.update_tracking_metadata(
                                    session_id,
                                    stabilisation_frames_remaining=stab - 1,
                                )
                                last_analyzed = now
                                continue

                            # Try OpenCV tracker first (lightweight)
                            bbox = None
                            if cv_tracker is not None:
                                bbox = await asyncio.to_thread(update_tracker, cv_tracker, frame)

                            if bbox:
                                analysis_frame = crop_candidate(frame, bbox)
                                candidate_identified = True
                                RuntimeManager.update_tracking_metadata(
                                    session_id,
                                    last_known_bbox=bbox,
                                    frames_since_last_verify=tracking_meta.get("frames_since_last_verify", 0) + 1,
                                )
                            else:
                                # Tracker lost — transition to LOST
                                RuntimeManager.update_tracking_metadata(
                                    session_id,
                                    tracking_status=TrackingStatus.LOST,
                                    last_known_bbox=None,
                                    tracking_failure_count=tracking_meta.get("tracking_failure_count", 0) + 1,
                                )
                                cv_tracker = None
                                log_event(logger, "tracking_lost", session_id=session_id)

                        elif tracking_status in (TrackingStatus.LOST, TrackingStatus.REVERIFYING):
                            candidate_embedding = tracking_meta.get("candidate_embedding")
                            cooldown = tracking_meta.get("frames_since_last_verify", 0)
                            consecutive_failures = tracking_meta.get("consecutive_verify_failures", 0)

                            # Cooldown: wait N frames between verification attempts
                            cooldown_required = VERIFY_COOLDOWN_FRAMES * (1 + consecutive_failures)
                            if candidate_embedding and cooldown >= cooldown_required:
                                from app.core.config import settings
                                RuntimeManager.update_tracking_metadata(
                                    session_id,
                                    tracking_status=TrackingStatus.REVERIFYING,
                                    frames_since_last_verify=0,
                                )

                                match = await asyncio.to_thread(
                                    verify_candidate,
                                    frame,
                                    candidate_embedding,
                                    settings.TRACKING_ACQUIRE_THRESHOLD,
                                    settings.TRACKING_RELEASE_THRESHOLD,
                                    currently_tracking=False,
                                )

                                if match:
                                    analysis_frame = crop_candidate(frame, match["bbox"])
                                    candidate_identified = True
                                    cv_tracker = create_tracker()
                                    init_tracker(cv_tracker, frame, match["bbox"])
                                    RuntimeManager.update_tracking_metadata(
                                        session_id,
                                        tracking_status=TrackingStatus.TRACKING,
                                        last_known_bbox=match["bbox"],
                                        confidence=match["confidence"],
                                        last_verified_timestamp=now,
                                        consecutive_verify_failures=0,
                                        reidentification_count=tracking_meta.get("reidentification_count", 0) + 1,
                                        stabilisation_frames_remaining=0,
                                    )
                                    log_event(logger, "tracking_reacquired",
                                              session_id=session_id,
                                              confidence=match["confidence"])
                                else:
                                    RuntimeManager.update_tracking_metadata(
                                        session_id,
                                        tracking_status=TrackingStatus.LOST,
                                        consecutive_verify_failures=consecutive_failures + 1,
                                    )
                            else:
                                # Still in cooldown — increment counter
                                RuntimeManager.update_tracking_metadata(
                                    session_id,
                                    frames_since_last_verify=cooldown + 1,
                                )

                        # ── Emit tracking status changes (state-change only) ──
                        current_ts = RuntimeManager.get_tracking_status(session_id)
                        if current_ts != last_tracking_status:
                            if last_tracking_status is not None:
                                logger.info(f"[ENROLLMENT DEBUG 11] WebSocket event emitted for TrackingStatus change: {last_tracking_status} -> {current_ts}")
                                await broadcast(session_id, {
                                    "type": "tracking_status",
                                    "status": current_ts.value if hasattr(current_ts, 'value') else str(current_ts),
                                })
                            last_tracking_status = current_ts

                        # ── Skip candidate-level analysis if enrolled but not identified ─
                        enrolled = tracking_meta and tracking_meta.get("candidate_embedding") is not None
                        if enrolled and not candidate_identified:
                            # Frame-level integrity still runs on full frame
                            try:
                                from app.ml.integrity.integrity_checker import check_integrity
                                integrity = await asyncio.to_thread(
                                    check_integrity, frame, {"face_detected": False, "direction": "missing", "confidence": 0.0},
                                    prev_state=integrity_state,
                                )
                                integrity_state = integrity.get("updated_state", {})
                                for event in integrity.get("events", []):
                                    await asyncio.to_thread(
                                        save_integrity_event, session_id, event
                                    )
                                    await broadcast(session_id, {
                                        "type": "integrity_alert",
                                        "event_type": event["event_type"],
                                        "severity": event["severity"],
                                        "details": str(event.get("details", "")),
                                    })
                            except ImportError:
                                pass
                            except Exception as e:
                                logger.warning(f"[INTEGRITY ERROR] {e}")

                            last_analyzed = now
                            continue  # Skip emotion/attention — candidate not visible

                        # ── Run emotion and attention on the analysis frame ───
                        emotion_start = time.time()
                        emotion, attention = await asyncio.gather(
                            asyncio.to_thread(analyze_frame, analysis_frame),
                            asyncio.to_thread(analyze_attention, analysis_frame),
                        )
                        logger.info(f"[TIMING] emotion/attention inference took {(time.time() - emotion_start)*1000:.1f}ms")

                        # Save & broadcast emotion (existing)
                        await asyncio.to_thread(save_emotion, session_id, emotion)
                        await broadcast(session_id, {
                            "type": "emotion",
                            "dominant_emotion": emotion["dominant_emotion"],
                            "confidence": emotion["confidence"],
                        })

                        # Save & broadcast attention (Phase 2)
                        await asyncio.to_thread(save_attention, session_id, attention)
                        await broadcast(session_id, {
                            "type": "attention",
                            "direction": attention["direction"],
                            "confidence": attention["confidence"],
                        })

                        # Phase 3: Integrity checks
                        # Frame-level (multi-face) uses full frame
                        # Candidate-level (liveness) uses attention from the analysis_frame
                        try:
                            from app.ml.integrity.integrity_checker import check_integrity
                            integrity = await asyncio.to_thread(
                                check_integrity, frame, attention,
                                prev_state=integrity_state,
                            )
                            integrity_state = integrity.get("updated_state", {})
                            for event in integrity.get("events", []):
                                await asyncio.to_thread(
                                    save_integrity_event, session_id, event
                                )
                                await broadcast(session_id, {
                                    "type": "integrity_alert",
                                    "event_type": event["event_type"],
                                    "severity": event["severity"],
                                    "details": str(event.get("details", "")),
                                })
                        except ImportError:
                            logger.debug("[INTEGRITY] integrity_checker module not installed, skipping")
                        except Exception as e:
                            logger.warning(f"[INTEGRITY ERROR] {e}")

                        logger.debug(
                            f"[EMOTION] {emotion['dominant_emotion']} "
                            f"({emotion['confidence']:.1f}%) "
                            f"[ATTENTION] {attention['direction']}"
                        )
                        last_analyzed = now
                    except asyncio.CancelledError:
                        raise
                    except Exception as e:
                        logger.warning(f"[EMOTION ERROR] {e}")

            # ── Audio — transcription + question generation ───────────────────────
            elif packet.stream.type == 'audio':
                try:
                    decoded_frames = packet.decode()
                    for frame in decoded_frames:
                        audio_buffer.append(frame)
                except Exception as e:
                    logger.warning(f"[RTMP] Audio decode error: {e}")

                if len(audio_buffer) >= 100:
                    frames_to_process = audio_buffer[:]
                    audio_buffer = []

                    if frames_to_process:
                        f = frames_to_process[0]
                        duration = sum(fr.samples for fr in frames_to_process) / f.sample_rate if f.sample_rate else 0
                        logger.info(f"[RTMP] audio packets received: {len(frames_to_process)}")
                        logger.info(f"[RTMP] sample rate: {f.sample_rate}")
                        logger.info(f"[RTMP] channels: {len(f.layout.channels) if f.layout else 'unknown'}")
                        logger.info(f"[RTMP] duration: {duration:.2f}s")

                    MAX_TRANSCRIBE_RETRIES = 2
                    transcript = None

                    for attempt in range(1, MAX_TRANSCRIBE_RETRIES + 1):
                        try:
                            whisper_start = time.time()
                            transcript = await asyncio.to_thread(
                                transcribe_chunk, frames_to_process
                            )
                            logger.info(f"[TIMING] whisper inference took {(time.time() - whisper_start)*1000:.1f}ms")
                            logger.info("transcription produced")
                            break
                        except asyncio.CancelledError:
                            raise
                        except Exception as e:
                            logger.warning(
                                f"[TRANSCRIPT] attempt {attempt}/{MAX_TRANSCRIBE_RETRIES} "
                                f"failed ({type(e).__name__}: {e})"
                            )
                            if attempt < MAX_TRANSCRIBE_RETRIES:
                                await asyncio.sleep(0.5)

                    if transcript is None:
                        logger.error(
                            f"[TRANSCRIPT] all {MAX_TRANSCRIBE_RETRIES} retries "
                            f"exhausted — dropping {len(frames_to_process)} "
                            f"audio packets for session {session_id}."
                        )
                        continue

                    transcript_chunk_count += 1

                    if job_id:
                        try:
                            from app.ml.speech.vocabulary_corrector import correct_transcript
                            from app.db.crud import get_job
                            job = await asyncio.to_thread(get_job, job_id)
                            if job:
                                transcript = correct_transcript(
                                    transcript,
                                    job_skills=job.extracted_skills or [],
                                    candidate_name="",
                                )
                        except Exception as e:
                            logger.warning(f"[VOCAB CORRECTION] {e}")

                    if not transcript or not transcript.strip():
                        continue

                    await asyncio.to_thread(save_transcript, session_id, transcript)
                    logger.info("transcript stored")

                    try:
                        sentiment = await asyncio.to_thread(
                            score_sentiment, transcript
                        )
                        await broadcast(session_id, {
                            "type": "sentiment",
                            "label": sentiment["label"],
                            "score": sentiment["score"],
                        })
                    except Exception as e:
                        logger.warning(f"[SENTIMENT ERROR] {e}")

                    await broadcast(session_id, {
                        "type": "transcript",
                        "text": transcript,
                    })
                    logger.info("websocket broadcast")

                    # ── Live competency evidence tracking (additive — no LLM) ──
                    try:
                        from app.ml.analysis.live_competency_tracker import LiveCompetencyTracker
                        LiveCompetencyTracker.update_from_transcript(session_id, transcript)
                        await broadcast(session_id, {
                            "type": "live_competency",
                            **LiveCompetencyTracker.get_snapshot(session_id),
                        })
                    except Exception as e:
                        logger.debug(f"[LIVE_COMPETENCY] update failed (non-fatal): {e}")

                    if transcript_chunk_count % (LLM_EVERY_N_CHUNKS + 1) == 0:
                        task = asyncio.create_task(
                            _generate_and_broadcast_questions(
                                session_id=session_id,
                                transcript=transcript,
                                job_id=job_id,
                            )
                        )
                        try:
                            from app.core.registry import add_tier2_task
                            add_tier2_task(session_id, task)
                        except Exception as e:
                            pass

                    try:
                        from app.ml.integrity.voice_detector import detect_voice_anomaly
                        from app.ml.speech.transcriber import get_audio_array
                    
                        voice_result = await asyncio.to_thread(
                            detect_voice_anomaly,
                            get_audio_array(frames_to_process)
                        )
                        if voice_result.get("anomaly_detected"):
                            await asyncio.to_thread(
                                save_integrity_event, session_id, {
                                    "event_type": f"voice_{voice_result['anomaly_type']}",
                                    "severity": "warning",
                                    "details": voice_result.get("details", {}),
                                }
                            )
                            await broadcast(session_id, {
                                "type": "integrity_alert",
                                "event_type": f"voice_{voice_result['anomaly_type']}",
                                "severity": "warning",
                                "details": str(voice_result.get("details", "")),
                            })
                    except ImportError:
                        pass
                    except Exception as e:
                        pass

        logger.info(f"[CONSUMER] Stream ended for session {session_id}")
    except Exception as e:
        logger.error(f"[CONSUMER] Error during stream processing: {e}")
        raise
    finally:
        if container:
            try:
                await asyncio.to_thread(container.close)
                logger.info(f"[CONSUMER] Cleaned up PyAV container for session {session_id}")
            except Exception as e:
                logger.error(f"[CONSUMER] Failed to close PyAV container: {e}")


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

            # Link question ID to live competency tracker
            try:
                from app.ml.analysis.live_competency_tracker import LiveCompetencyTracker
                LiveCompetencyTracker.link_question(session_id, question_id, transcript)
            except Exception:
                pass  # Non-critical — never block question pipeline

        # Log STAR feedback and confidence score — used in session report
        if result.get("star_feedback"):
            logger.info(f"[STAR] {result['star_feedback']}")
        if result.get("confidence_score"):
            logger.info(f"[CONFIDENCE] {result['confidence_score']}/10")

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.warning(f"[LLM ERROR] question generation failed: {e}")