"""
Audio cleaner — noise reduction and normalization for Whisper input.

Applies a pre-processing pipeline to raw audio before transcription:
1. Noise reduction (via noisereduce library)
2. Peak normalization (to -3dB)
3. Silence trimming (remove leading/trailing silence)

Improves Whisper accuracy, especially in noisy environments
like home offices or shared spaces.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)


def clean_audio(
    audio_array: np.ndarray,
    sample_rate: int = 16000,
) -> np.ndarray:
    """
    Clean audio for better transcription quality.

    Args:
        audio_array: float32 numpy array of audio samples
        sample_rate: audio sample rate (Whisper expects 16kHz)

    Returns:
        Cleaned float32 numpy array, same sample rate.
    """
    if audio_array is None or len(audio_array) == 0:
        return audio_array

    # Step 1: Noise reduction
    audio_array = _reduce_noise(audio_array, sample_rate)

    # Step 2: Silence trimming
    audio_array = _trim_silence(audio_array)

    # Step 3: Peak normalization
    audio_array = _normalize(audio_array)

    return audio_array


def _reduce_noise(audio: np.ndarray, sample_rate: int) -> np.ndarray:
    """Apply spectral gating noise reduction."""
    try:
        import noisereduce as nr
        return nr.reduce_noise(
            y=audio,
            sr=sample_rate,
            prop_decrease=0.6,  # how much to reduce noise (0-1)
            stationary=True,    # assume stationary background noise
        )
    except ImportError:
        logger.warning("[AUDIO_CLEANER] noisereduce not installed — skipping noise reduction")
        return audio
    except Exception as e:
        logger.warning(f"[AUDIO_CLEANER] noise reduction failed: {e}")
        return audio


def _normalize(audio: np.ndarray, target_db: float = -3.0) -> np.ndarray:
    """
    Peak normalize audio to target dB level.
    -3 dB is a safe headroom that avoids clipping.
    """
    peak = np.max(np.abs(audio))
    if peak < 1e-8:
        return audio  # silence — don't amplify noise

    target_amplitude = 10 ** (target_db / 20)
    return audio * (target_amplitude / peak)


def _trim_silence(
    audio: np.ndarray,
    threshold: float = 0.01,
    frame_size: int = 1600,  # 100ms at 16kHz
) -> np.ndarray:
    """
    Trim leading and trailing silence.
    Keeps at least 1 frame of padding on each side.
    """
    if len(audio) < frame_size * 3:
        return audio  # too short to trim

    # Find first frame above threshold
    start = 0
    for i in range(0, len(audio) - frame_size, frame_size):
        if np.max(np.abs(audio[i:i + frame_size])) > threshold:
            start = max(0, i - frame_size)  # keep 1 frame padding
            break

    # Find last frame above threshold
    end = len(audio)
    for i in range(len(audio) - frame_size, frame_size, -frame_size):
        if np.max(np.abs(audio[i:i + frame_size])) > threshold:
            end = min(len(audio), i + frame_size * 2)  # keep 1 frame padding
            break

    trimmed = audio[start:end]
    return trimmed if len(trimmed) > frame_size else audio
