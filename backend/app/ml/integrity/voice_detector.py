"""
Voice anomaly detector — detects background voices and speaker anomalies.

Uses energy-based voice activity detection (VAD) to identify:
- Sudden energy spikes (possible background speaker)
- Multi-speaker patterns (energy variance anomalies)

This is NOT full speaker diarization — it's a lightweight anomaly
detector designed to flag suspicious audio patterns without heavy ML.
"""

import logging
import numpy as np

logger = logging.getLogger(__name__)

# Energy spike threshold: if a segment's energy is this many times
# higher than the rolling average, flag it as an anomaly
ENERGY_SPIKE_RATIO = 3.0

# Minimum number of audio frames to analyze
MIN_FRAMES = 1600  # ~100ms at 16kHz


def detect_voice_anomaly(audio_array: np.ndarray, sample_rate: int = 16000) -> dict:
    """
    Detect voice anomalies in an audio chunk.

    Args:
        audio_array: float32 numpy array of audio samples (normalized)
        sample_rate: audio sample rate

    Returns:
        {
            "anomaly_detected": bool,
            "confidence": float (0-1),
            "anomaly_type": str | None,  # "energy_spike", "multi_speaker"
            "details": dict,
        }
    """
    if audio_array is None or len(audio_array) < MIN_FRAMES:
        return _no_anomaly()

    try:
        # Split audio into short segments (~200ms each)
        segment_size = int(sample_rate * 0.2)
        segments = [
            audio_array[i:i + segment_size]
            for i in range(0, len(audio_array) - segment_size + 1, segment_size)
        ]

        if len(segments) < 3:
            return _no_anomaly()

        # Compute RMS energy for each segment
        energies = np.array([
            np.sqrt(np.mean(seg ** 2)) for seg in segments
        ])

        # Filter out silence (very low energy segments)
        noise_floor = np.percentile(energies, 10)
        active_energies = energies[energies > noise_floor * 2]

        if len(active_energies) < 2:
            return _no_anomaly()

        # ── Energy spike detection ───────────────────────────────────────
        mean_energy = np.mean(active_energies)
        max_energy = np.max(active_energies)

        if mean_energy > 0 and max_energy / mean_energy > ENERGY_SPIKE_RATIO:
            spike_confidence = min(1.0, (max_energy / mean_energy - ENERGY_SPIKE_RATIO) / 3.0)
            return {
                "anomaly_detected": True,
                "confidence": round(spike_confidence, 3),
                "anomaly_type": "energy_spike",
                "details": {
                    "max_energy": round(float(max_energy), 4),
                    "mean_energy": round(float(mean_energy), 4),
                    "ratio": round(float(max_energy / mean_energy), 2),
                },
            }

        # ── Multi-speaker pattern detection ──────────────────────────────
        # High variance in energy can indicate multiple speakers
        energy_std = np.std(active_energies)
        energy_cv = energy_std / mean_energy if mean_energy > 0 else 0

        # Coefficient of variation > 0.8 is suspicious
        if energy_cv > 0.8:
            ms_confidence = min(1.0, (energy_cv - 0.8) / 0.5)
            return {
                "anomaly_detected": True,
                "confidence": round(ms_confidence, 3),
                "anomaly_type": "multi_speaker",
                "details": {
                    "energy_cv": round(float(energy_cv), 3),
                    "energy_std": round(float(energy_std), 4),
                    "segments_analyzed": len(active_energies),
                },
            }

        return _no_anomaly()

    except Exception as e:
        logger.warning(f"[VOICE_DETECTOR] analysis failed: {e}")
        return _no_anomaly()


def _no_anomaly() -> dict:
    return {
        "anomaly_detected": False,
        "confidence": 0.0,
        "anomaly_type": None,
        "details": {},
    }
