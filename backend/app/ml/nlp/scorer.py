"""
NLP scoring module.

scorer.py — sentiment analysis + Big Five personality trait estimation.

Sentiment: uses distilbert-base-uncased-finetuned-sst-2-english via HuggingFace
           (lightweight, runs fully locally, no data leaves the server)

Big Five:  keyword frequency approach based on Mairesse et al. (2007).
           Not a clinical instrument — used as a directional signal only.
"""

import logging
from transformers import pipeline

logger = logging.getLogger(__name__)

# ── Load models once at import time ──────────────────────────────────────────
# This happens when the FastAPI server starts, not on each request.

logger.info("[NLP] Loading sentiment model...")
_sentiment_pipe = pipeline(
    "sentiment-analysis",
    model="distilbert-base-uncased-finetuned-sst-2-english",
    truncation=True,
    max_length=512,
)
logger.info("[NLP] Sentiment model ready.")

# ── Big Five keyword lexicon ──────────────────────────────────────────────────
# Each list contains words strongly associated with the trait.
# Based on Mairesse et al., "Using Linguistic Cues for the Automatic
# Recognition of Personality", JAIR 30:457–500 (2007).

_BIG_FIVE_KEYWORDS: dict[str, list[str]] = {
    "openness": [
        "creative", "imagine", "curious", "novel", "explore", "ideas",
        "innovative", "artistic", "abstract", "philosophical", "experiment",
        "vision", "insight", "unconventional", "inventive",
    ],
    "conscientiousness": [
        "organized", "plan", "deadline", "detail", "thorough", "responsible",
        "systematic", "careful", "precise", "structured", "diligent",
        "efficient", "prioritize", "accountable", "disciplined",
    ],
    "extraversion": [
        "team", "collaborate", "lead", "present", "communicate", "energize",
        "social", "enthusiastic", "assertive", "outgoing", "network",
        "motivate", "influence", "talkative", "engaging",
    ],
    "agreeableness": [
        "support", "help", "empathy", "listen", "cooperate", "trust",
        "kind", "considerate", "flexible", "compromise", "harmony",
        "patient", "understanding", "respectful", "nurture",
    ],
    "neuroticism": [
        "stress", "anxious", "worry", "pressure", "nervous", "overwhelm",
        "tense", "frustrated", "uncertain", "doubt", "fear",
        "struggle", "difficult", "challenging", "setback",
    ],
}


# ── Public API ────────────────────────────────────────────────────────────────

def score_sentiment(text: str) -> dict:
    """
    Returns sentiment label (POSITIVE/NEGATIVE) and confidence score (0–1).
    Text is truncated to 512 tokens by the pipeline automatically.

    Also includes sample_confidence (0–1) based on text length:
    - < 20 words → 0.0 (too short for reliable sentiment)
    - 20–100 words → linear ramp
    - 100+ words → 1.0

    Example return: {"label": "POSITIVE", "score": 0.987, "sample_confidence": 0.8}
    """
    if not text or not text.strip():
        return {"label": "NEUTRAL", "score": 0.0, "sample_confidence": 0.0}

    # Sample confidence based on text length
    word_count = len(text.split())
    if word_count < 20:
        sample_confidence = 0.0
    elif word_count >= 100:
        sample_confidence = 1.0
    else:
        sample_confidence = round((word_count - 20) / 80, 3)

    try:
        result = _sentiment_pipe(text[:1024])[0]
        return {
            "label": result["label"],
            "score": round(float(result["score"]), 3),
            "sample_confidence": sample_confidence,
        }
    except Exception as e:
        logger.warning(f"[NLP] Sentiment scoring failed: {e}")
        return {"label": "NEUTRAL", "score": 0.0, "sample_confidence": 0.0}


def score_big_five(full_transcript: str) -> dict:
    """
    Returns Big Five trait scores on a 0–10 scale based on keyword frequency.
    Normalised by word count so longer transcripts don't inflate scores.

    Also includes per-trait confidence and an overall confidence score
    based on transcript length and keyword hit density.

    Example return:
    {
        "scores": {
            "openness": 3.2,
            "conscientiousness": 5.1,
            ...
        },
        "confidence": {
            "openness": 0.6,
            "conscientiousness": 0.8,
            ...
        },
        "overall_confidence": 0.7,
    }

    For backwards compatibility, trait scores are also available as
    top-level keys (e.g. result["openness"]).
    """
    if not full_transcript or not full_transcript.strip():
        empty_scores = {trait: 0.0 for trait in _BIG_FIVE_KEYWORDS}
        empty_conf = {trait: 0.0 for trait in _BIG_FIVE_KEYWORDS}
        result = {**empty_scores, "scores": empty_scores, "confidence": empty_conf, "overall_confidence": 0.0}
        return result

    text = full_transcript.lower()
    word_count = max(len(text.split()), 1)

    # Base confidence from transcript length
    if word_count < 50:
        length_confidence = 0.0
    elif word_count >= 200:
        length_confidence = 1.0
    else:
        length_confidence = round((word_count - 50) / 150, 3)

    scores = {}
    confidences = {}

    for trait, keywords in _BIG_FIVE_KEYWORDS.items():
        hits = sum(text.count(kw) for kw in keywords)
        # Scale: hits per 100 words, capped at 10
        raw = (hits / word_count) * 100
        scores[trait] = round(min(raw * 10, 10.0), 2)

        # Per-trait confidence: length_confidence * hit boost
        hit_boost = min(hits / 3, 1.0) * 0.2  # up to +0.2 for 3+ hits
        confidences[trait] = round(min(length_confidence + hit_boost, 1.0), 3)

    overall_confidence = round(
        sum(confidences.values()) / max(len(confidences), 1), 3
    )

    # Return with backwards-compatible top-level keys
    result = {
        **scores,
        "scores": scores,
        "confidence": confidences,
        "overall_confidence": overall_confidence,
    }
    return result