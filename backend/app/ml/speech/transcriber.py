import logging
import whisper
import numpy as np

logger = logging.getLogger(__name__)

model = whisper.load_model("small")  # Phase 4: upgraded from "base" for ~4x accuracy


import av

def get_audio_array(audio_packets: list) -> np.ndarray:
    resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)
    frames = []
    for packet in audio_packets:
        # PyAV demuxes Packet objects, they need to be decoded into AudioFrames
        for frame in packet.decode():
            # Resample to 16kHz mono float for Whisper
            for rf in resampler.resample(frame):
                frames.append(rf.to_ndarray().flatten())
    # Flush resampler
    for rf in resampler.resample(None) or []:
        frames.append(rf.to_ndarray().flatten())
        
    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames).astype(np.float32)

def transcribe_chunk(audio_packets: list) -> str:
    audio_array = get_audio_array(audio_packets)
    if len(audio_array) == 0:
        return ""

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