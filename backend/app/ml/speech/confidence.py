"""
Transcription confidence scorer.

Evaluates the quality/reliability of a Whisper transcription
using segment-level metrics from Whisper's output:
- avg_logprob: higher = more confident
- no_speech_prob: lower = more likely speech was present

Returns a single 0.0–1.0 confidence score.
"""

import logging

logger = logging.getLogger(__name__)


def score_transcription_confidence(result: dict) -> float:
    """
    Score transcription confidence from Whisper's full result dict.

    Args:
        result: Whisper result dict containing "segments" with
                "avg_logprob" and "no_speech_prob" per segment.

    Returns:
        float 0.0–1.0 confidence score.
    """
    segments = result.get("segments", [])

    if not segments:
        return 0.0

    total_logprob = 0.0
    total_no_speech = 0.0
    count = 0

    for seg in segments:
        avg_logprob = seg.get("avg_logprob", -1.0)
        no_speech_prob = seg.get("no_speech_prob", 0.5)

        total_logprob += avg_logprob
        total_no_speech += no_speech_prob
        count += 1

    if count == 0:
        return 0.0

    avg_logprob = total_logprob / count
    avg_no_speech = total_no_speech / count

    # avg_logprob typically ranges from -1.0 (bad) to 0.0 (perfect)
    # Map -1.0 → 0.0 and 0.0 → 1.0
    logprob_score = max(0.0, min(1.0, avg_logprob + 1.0))

    # no_speech_prob: 0.0 = definitely speech, 1.0 = no speech
    speech_score = 1.0 - avg_no_speech

    # Weighted combination (logprob is more reliable)
    confidence = logprob_score * 0.7 + speech_score * 0.3

    return round(confidence, 3)
