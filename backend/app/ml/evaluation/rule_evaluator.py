import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

def evaluate_rules(transcript: str, domain: str, rubric: Dict[str, Any]) -> float:
    """
    Evaluates the transcript against domain-specific rules (e.g., keyword matching).
    Returns a score between 0.0 and 10.0.
    """
    if not transcript or not transcript.strip():
        return 0.0

    transcript_lower = transcript.lower()
    required_skills = rubric.get("required_skills", [])
    
    if not required_skills:
        return 5.0  # Neutral score if no specific rules
        
    matches = sum(1 for skill in required_skills if skill.lower() in transcript_lower)
    coverage = matches / len(required_skills)
    
    # Scale to 10
    score = coverage * 10.0
    return min(max(score, 0.0), 10.0)
