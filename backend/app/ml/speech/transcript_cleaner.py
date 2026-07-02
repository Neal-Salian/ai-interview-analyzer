"""
Transcript cleaner — post-processing for Whisper output.

Removes common Whisper artifacts:
- Repeated words/phrases (stuttering)
- Hallucinated artifacts like "[Music]", "(inaudible)"
- Normalizes punctuation and whitespace

Does NOT change the meaning of the transcript — only cleans up
formatting and recognition artifacts.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Whisper commonly hallucinates these when audio is unclear
_WHISPER_ARTIFACTS = [
    r"\[Music\]",
    r"\[music\]",
    r"\(inaudible\)",
    r"\(Inaudible\)",
    r"\[BLANK_AUDIO\]",
    r"\[blank_audio\]",
    r"\*\*\*",
    r"\.{4,}",                       # excessive dots
    r"♪+",                           # music symbols
    r"\[Applause\]",
    r"\(applause\)",
    r"Thank you for watching\.?$",   # common Whisper hallucination at end
    r"Thanks for watching\.?$",
    r"Please subscribe\.?$",
    r"See you next time\.?$",
]

# Compiled pattern for artifact removal
_ARTIFACT_PATTERN = re.compile("|".join(_WHISPER_ARTIFACTS), re.IGNORECASE)

# Pattern for repeated consecutive words: "the the" → "the"
_REPEATED_WORD = re.compile(r"\b(\w+)(\s+\1){1,}\b", re.IGNORECASE)

# Pattern for excessive whitespace
_MULTI_SPACE = re.compile(r"\s{2,}")


def clean_transcript(text: str) -> str:
    """
    Clean Whisper transcript output.

    Args:
        text: raw Whisper output string

    Returns:
        Cleaned transcript string.
    """
    if not text or not text.strip():
        return text

    # Step 1: Remove Whisper artifacts
    text = _ARTIFACT_PATTERN.sub("", text)

    # Step 2: Remove repeated consecutive words
    text = _REPEATED_WORD.sub(r"\1", text)

    # Step 3: Normalize whitespace
    text = _MULTI_SPACE.sub(" ", text)

    # Step 4: Clean up punctuation
    text = text.replace(" ,", ",")
    text = text.replace(" .", ".")
    text = text.replace(" ?", "?")
    text = text.replace(" !", "!")
    text = text.replace(",,", ",")
    text = text.replace("..", ".")

    # Step 5: Trim
    text = text.strip()

    # Step 6: Ensure first letter is capitalized
    if text and text[0].islower():
        text = text[0].upper() + text[1:]

    logger.info("transcript cleaner output")
    return text
