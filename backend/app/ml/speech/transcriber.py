import logging
import whisper
import numpy as np

logger = logging.getLogger(__name__)

model = None
import threading
_whisper_lock = threading.Lock()

def _get_model():
    global model
    if model is None:
        with _whisper_lock:
            if model is None:
                import os
                weights_path = "/app/models/small.pt"
                local_weights_path = os.path.expanduser("~/.cache/whisper/small.pt")
                if os.path.exists(weights_path):
                    model = whisper.load_model("small", download_root="/app/models")
                elif os.path.exists(local_weights_path):
                    logger.info(f"Using local Whisper model path: {local_weights_path}")
                    model = whisper.load_model("small")
                else:
                    raise FileNotFoundError(f"Whisper weights not found at {weights_path} or {local_weights_path}. Automatic download disabled.")
                logger.info("model loaded successfully")
                logger.info(f"[WHISPER] model loaded from scratch: {id(model)}")
            else:
                logger.info(f"[WHISPER] model loaded from preload: {id(model)}")
    else:
        logger.info(f"[WHISPER] model loaded from preload: {id(model)}")
    return model

import av

def get_audio_array(audio_frames: list) -> np.ndarray:
    resampler = av.AudioResampler(format='flt', layout='mono', rate=16000)
    frames = []
    
    # audio_frames already contains decoded av.AudioFrame objects
    for frame in audio_frames:
        # Resample to 16kHz mono float for Whisper
        for rf in resampler.resample(frame):
            frames.append(rf.to_ndarray().flatten())
            
    # Flush resampler
    for rf in resampler.resample(None) or []:
        frames.append(rf.to_ndarray().flatten())
        
    if not frames:
        return np.array([], dtype=np.float32)
    return np.concatenate(frames).astype(np.float32)

def transcribe_chunk(audio_frames: list) -> str:
    """
    Takes a list of audio frames, converts to numpy array, cleans audio,
    and returns transcript.
    """
    import time
    start_time = time.time()
    logger.info("[WHISPER] transcribe_chunk() is entered")
    
    audio_array = get_audio_array(audio_frames)
    if len(audio_array) == 0:
        logger.info("[WHISPER] transcribe_chunk() exits (empty audio)")
        return ""

    # Phase 4: Pre-processing — noise reduction + normalization + silence trim
    try:
        from app.ml.speech.audio_cleaner import clean_audio
        audio_array = clean_audio(audio_array)
    except Exception as e:
        logger.warning(f"[TRANSCRIBER] audio cleaning failed, using raw: {e}")

    import math
    
    # Calculate audio properties
    sample_rate = 16000
    channels = 1
    dtype = str(audio_array.dtype)
    shape = audio_array.shape
    duration = len(audio_array) / sample_rate
    rms = float(np.sqrt(np.mean(audio_array**2)))
    peak_amplitude = float(np.max(np.abs(audio_array)))
    whisper_model_name = "small"
    decode_params = "fp16=False, temperature=0.0, language='en', condition_on_previous_text=False"

    logger.info(f"sample rate: {sample_rate}")
    logger.info(f"channels: {channels}")
    logger.info(f"dtype: {dtype}")
    logger.info(f"shape: {shape}")
    logger.info(f"duration: {duration:.3f}")
    logger.info(f"RMS: {rms:.5f}")
    logger.info(f"peak amplitude: {peak_amplitude:.5f}")
    logger.info(f"language parameter: en")
    logger.info(f"Whisper model name: {whisper_model_name}")
    logger.info(f"decode parameters: {decode_params}")

    m = _get_model()
    logger.info(f"[WHISPER] which model instance is used: {id(m)}")
    logger.info(f"[WHISPER] memory address/id: {id(m)}")
    
    # Whisper can hang on silence with temperature fallback, so disable fallback and force English
    result = m.transcribe(audio_array, fp16=False, temperature=0.0, language="en", condition_on_previous_text=False)
    
    text = result["text"].strip()

    # Phase 4: Post-processing — remove Whisper artifacts + deduplicate words
    try:
        from app.ml.speech.transcript_cleaner import clean_transcript
        text = clean_transcript(text)
    except Exception as e:
        logger.warning(f"[TRANSCRIBER] transcript cleaning failed, using raw: {e}")

    time_taken = time.time() - start_time
    logger.info(f"[WHISPER] transcribe_chunk() exits")
    logger.info(f"[WHISPER] time taken: {time_taken:.2f}s")
    logger.info(f"[WHISPER] returned text: {text}")

    return text
