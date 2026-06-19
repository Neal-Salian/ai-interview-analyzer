import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

# Basic fallback rubrics if domain detection is weak
DEFAULT_RUBRICS = {
    "software": {
        "required_skills": ["coding", "architecture", "debugging"],
        "tone": "technical and analytical"
    },
    "finance": {
        "required_skills": ["accounting principles", "financial modeling", "compliance"],
        "tone": "detail-oriented and precise"
    },
    "hr": {
        "required_skills": ["people management", "conflict resolution", "policy awareness"],
        "tone": "empathetic and professional"
    },
    "sales": {
        "required_skills": ["persuasion", "customer focus", "strategy"],
        "tone": "confident and engaging"
    },
    "general": {
        "required_skills": ["communication", "problem solving", "adaptability"],
        "tone": "professional"
    }
}


def detect_domain(job_title: str, job_description: str) -> str:
    """
    Detects the primary domain based on keywords in title and description.
    In a real-world scenario, this could also use an LLM for classification.
    """
    text = f"{job_title} {job_description}".lower()
    
    if any(k in text for k in ["engineer", "developer", "programmer", "software", "coder"]):
        return "software"
    if any(k in text for k in ["accountant", "finance", "audit", "tax", "cpa", "financial"]):
        return "finance"
    if any(k in text for k in ["hr", "human resources", "recruiter", "talent"]):
        return "hr"
    if any(k in text for k in ["sales", "marketing", "account executive", "b2b"]):
        return "sales"
        
    return "general"


def get_evaluation_rubric(domain: str) -> Dict[str, Any]:
    """
    Returns a domain-specific evaluation rubric.
    """
    return DEFAULT_RUBRICS.get(domain, DEFAULT_RUBRICS["general"])
