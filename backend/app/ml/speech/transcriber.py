import logging
import whisper
import numpy as np

logger = logging.getLogger(__name__)

model = whisper.load_model("small")  # Phase 4: upgraded from "base" for ~4x accuracy


def transcribe_chunk(audio_packets: list) -> str:
    audio_array = np.concatenate([
        packet.to_ndarray() for packet in audio_packets
    ]).flatten().astype(np.float32)

    # Normalize (with epsilon to prevent division by zero)
    audio_array = audio_array / (np.max(np.abs(audio_array)) + 1e-8)

    # Phase 4: Pre-processing — noise reduction + normalization + silence trim
    try:
        from app.ml.speech.audio_cleaner import clean_audio
        audio_array = clean_audio(audio_array)
    except Exception as e:
        logger.warning(f"[TRANSCRIBER] audio cleaning failed, using raw: {e}")

    result = model.transcribe(audio_array, fp16=False)
    
    text = result["text"].strip()

    # Phase 4: Post-processing — remove Whisper artifacts + deduplicate words
    try:
        from app.ml.speech.transcript_cleaner import clean_transcript
        text = clean_transcript(text)
    except Exception as e:
        logger.warning(f"[TRANSCRIBER] transcript cleaning failed, using raw: {e}")

    return text