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
    logger.info(f"raw transcript: '{text}'")
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

    # Step 2: Remove repeated consecutive words (DISABLED to avoid removing valid stutters)
    # text = _REPEATED_WORD.sub(r"\1", text)

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

    logger.info(f"cleaned transcript: '{text}'")
    return text

def deduplicate_overlap(prev_text: str, curr_text: str) -> str:
    """
    Removes overlapping words at the beginning of curr_text that match the end of prev_text.
    Used for concatenating overlapping audio chunks without duplicating words.
    """
    if not prev_text or not curr_text:
        return curr_text
        
    def normalize(text):
        return re.sub(r'[^\w\s]', '', text.lower()).strip()
        
    prev_words = normalize(prev_text).split()
    curr_words = normalize(curr_text).split()
    
    # Check overlaps from max possible overlap down to 1 word
    # Overlap shouldn't be more than 10 words (usually 2-5 words for ~400ms overlap)
    max_overlap = min(len(prev_words), len(curr_words), 10) 
    
    overlap_len = 0
    for i in range(max_overlap, 0, -1):
        if prev_words[-i:] == curr_words[:i]:
            overlap_len = i
            break
            
    if overlap_len > 0:
        overlap_words = curr_words[:overlap_len]
        pattern_str = r'^\s*([^\w\s]*\s*)?'
        for word in overlap_words:
            pattern_str += re.escape(word) + r'\b[\s\W]*'
            
        pattern = re.compile(pattern_str, re.IGNORECASE)
        match = pattern.match(curr_text)
        if match:
            return curr_text[match.end():].strip()
            
    return curr_text
