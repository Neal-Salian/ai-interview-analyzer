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

    Example return: {"label": "POSITIVE", "score": 0.987}
    """
    if not text or not text.strip():
        return {"label": "NEUTRAL", "score": 0.0}

    try:
        result = _sentiment_pipe(text[:1024])[0]
        return {
            "label": result["label"],
            "score": round(float(result["score"]), 3),
        }
    except Exception as e:
        logger.warning(f"[NLP] Sentiment scoring failed: {e}")
        return {"label": "NEUTRAL", "score": 0.0}


def score_big_five(full_transcript: str) -> dict:
    """
    Returns Big Five trait scores on a 0–10 scale based on keyword frequency.
    Normalised by word count so longer transcripts don't inflate scores.

    Example return:
    {
        "openness": 3.2,
        "conscientiousness": 5.1,
        "extraversion": 4.0,
        "agreeableness": 2.8,
        "neuroticism": 1.4
    }
    """
    if not full_transcript or not full_transcript.strip():
        return {trait: 0.0 for trait in _BIG_FIVE_KEYWORDS}

    text = full_transcript.lower()
    word_count = max(len(text.split()), 1)
    scores = {}

    for trait, keywords in _BIG_FIVE_KEYWORDS.items():
        hits = sum(text.count(kw) for kw in keywords)
        # Scale: hits per 100 words, capped at 10
        raw = (hits / word_count) * 100
        scores[trait] = round(min(raw * 10, 10.0), 2)

    return scores