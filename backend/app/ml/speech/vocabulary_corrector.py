"""
Vocabulary corrector — job-skill-based transcript correction.

Post-processes Whisper output to fix misrecognized technical terms
using fuzzy matching against the job's extracted_skills list and
candidate name.

Uses difflib.get_close_matches() — no new dependencies required.
Does NOT change transcript meaning — only corrects spelling/recognition.
"""

import re
import logging
from difflib import get_close_matches

logger = logging.getLogger(__name__)

# Minimum similarity ratio for fuzzy matching (0.0 - 1.0)
MIN_SIMILARITY = 0.75

# Minimum word length to consider for correction
MIN_WORD_LENGTH = 4


def correct_transcript(
    text: str,
    job_skills: list[str] | None = None,
    candidate_name: str = "",
) -> str:
    """
    Correct technical terms and names in the transcript.

    Args:
        text: Whisper output (already cleaned by transcript_cleaner)
        job_skills: list of extracted skills from Job.extracted_skills
        candidate_name: candidate's name for name correction

    Returns:
        Corrected transcript string.
    """
    if not text or not text.strip():
        return text

    # Build vocabulary from job skills
    vocabulary = _build_vocabulary(job_skills or [])

    # Correct candidate name if provided
    if candidate_name:
        text = _correct_name(text, candidate_name)

    # Correct technical terms
    if vocabulary:
        text = _correct_terms(text, vocabulary)

    return text


def _build_vocabulary(job_skills: list[str]) -> dict[str, str]:
    """
    Build a lowercase → canonical mapping from job skills.

    E.g., ["React.js", "Node.js", "PostgreSQL"]
    → {"react.js": "React.js", "node.js": "Node.js", "postgresql": "PostgreSQL",
       "react": "React.js", "node": "Node.js", "postgres": "PostgreSQL"}
    """
    vocab = {}
    for skill in job_skills:
        if not skill:
            continue
        canonical = skill.strip()
        vocab[canonical.lower()] = canonical

        # Also add shortened versions (without .js, etc.)
        base = re.sub(r"\.(js|ts|py|rb|go|rs)$", "", canonical, flags=re.IGNORECASE)
        if base.lower() != canonical.lower():
            vocab[base.lower()] = canonical

    return vocab


def _correct_name(text: str, candidate_name: str) -> str:
    """
    Fix candidate name recognition errors.

    Whisper often mishears proper nouns. If a word in the transcript
    is phonetically similar to the candidate's name, replace it.
    """
    name_parts = candidate_name.split()
    words = text.split()
    corrected = []

    for word in words:
        clean_word = re.sub(r"[^\w]", "", word)
        if len(clean_word) < 3:
            corrected.append(word)
            continue

        for name_part in name_parts:
            matches = get_close_matches(
                clean_word.lower(),
                [name_part.lower()],
                n=1,
                cutoff=0.7,
            )
            if matches:
                # Preserve original punctuation
                prefix = word[:len(word) - len(word.lstrip(r"\"'("))]
                suffix = word[len(word.rstrip(r"\"'.,!?;:)")):]
                word = prefix + name_part + suffix
                break

        corrected.append(word)

    return " ".join(corrected)


def _correct_terms(text: str, vocabulary: dict[str, str]) -> str:
    """
    Fix technical term recognition using fuzzy matching.

    Only corrects words that are close to a known skill term.
    Won't change words that are already correct.
    """
    vocab_keys = list(vocabulary.keys())
    words = text.split()
    corrected = []

    for word in words:
        clean_word = re.sub(r"[^\w.]", "", word)  # keep dots for React.js etc.

        if len(clean_word) < MIN_WORD_LENGTH:
            corrected.append(word)
            continue

        # Check exact match first (no correction needed)
        if clean_word.lower() in vocabulary:
            # Replace with canonical casing
            canonical = vocabulary[clean_word.lower()]
            prefix = word[:word.find(clean_word)]
            suffix = word[word.find(clean_word) + len(clean_word):]
            corrected.append(prefix + canonical + suffix)
            continue

        # Fuzzy match against vocabulary
        matches = get_close_matches(
            clean_word.lower(),
            vocab_keys,
            n=1,
            cutoff=MIN_SIMILARITY,
        )

        if matches:
            canonical = vocabulary[matches[0]]
            prefix = word[:word.find(clean_word)]
            suffix = word[word.find(clean_word) + len(clean_word):]
            corrected.append(prefix + canonical + suffix)
            logger.debug(f"[VOCAB] Corrected '{clean_word}' → '{canonical}'")
        else:
            corrected.append(word)

    return " ".join(corrected)
