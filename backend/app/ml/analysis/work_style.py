"""
Work-style inference — optional post-plugin interpretation layer.

Combines competency scores into work-style insights.  This layer is
strictly one-directional:

    Competencies → Work-Style Insights

Work-style insights NEVER influence competency scores.  They are purely
an interpretation layer for recruiter reports.

Every inference includes a mandatory disclaimer:
    "This inference is based only on interview evidence and should not
     be interpreted as a clinical or psychological assessment."
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ── Mandatory disclaimer ─────────────────────────────────────────────────────

WORK_STYLE_DISCLAIMER = (
    "This inference is based only on interview evidence and should not "
    "be interpreted as a clinical or psychological assessment."
)

# ── Work-style patterns ──────────────────────────────────────────────────────
# Each pattern defines which competencies contribute and what the insight means.

_WORK_STYLE_PATTERNS = [
    {
        "insight": "Leadership Potential",
        "requires": ["leadership", "confidence", "communication"],
        "threshold": 60,
        "description_strong": (
            "Interview evidence suggests strong leadership orientation. "
            "The candidate demonstrated ownership, decision-making ability, "
            "and confident communication."
        ),
        "description_moderate": (
            "Interview evidence suggests emerging leadership qualities. "
            "Some indicators of ownership and decision-making were observed."
        ),
    },
    {
        "insight": "Collaborative Work Style",
        "requires": ["teamwork", "communication", "engagement"],
        "threshold": 60,
        "description_strong": (
            "Interview evidence suggests a strongly collaborative work style. "
            "The candidate demonstrated team orientation, effective communication, "
            "and active engagement."
        ),
        "description_moderate": (
            "Interview evidence suggests willingness to collaborate. "
            "Some indicators of team orientation were observed."
        ),
    },
    {
        "insight": "Growth Orientation",
        "requires": ["adaptability"],
        "optional": ["engagement"],
        "threshold": 60,
        "description_strong": (
            "Interview evidence suggests strong growth orientation. "
            "The candidate demonstrated learning agility and comfort with change."
        ),
        "description_moderate": (
            "Interview evidence suggests openness to learning and growth. "
            "Some indicators of adaptability were observed."
        ),
    },
    {
        "insight": "Pressure Management",
        "requires": ["emotional_stability"],
        "optional": ["stress_indicators", "confidence"],
        "threshold": 60,
        "description_strong": (
            "Interview evidence suggests strong composure under pressure. "
            "The candidate maintained emotional stability and confidence "
            "throughout the interview."
        ),
        "description_moderate": (
            "Interview evidence suggests adequate pressure management. "
            "Some fluctuation in composure was observed but within normal range."
        ),
    },
]


def infer_work_styles(
    results: list,
) -> list[dict[str, Any]]:
    """
    Infer work-style insights from competency scores.

    Args:
        results: list of EnhancedMetricResult objects from the aggregator

    Returns:
        List of work-style insight dicts, each containing:
          - insight: human-readable name
          - strength: "strong" | "moderate" | "limited"
          - contributing_competencies: list of {name, score}
          - description: evidence-based description
          - confidence: 0.0–1.0
          - disclaimer: mandatory disclaimer text

    This function NEVER modifies the input results.
    """
    if not results:
        return []

    # Build a lookup: metric_key → result
    score_lookup = {}
    for r in results:
        key = r.name.lower().replace(" ", "_")
        score_lookup[key] = {
            "name": r.name,
            "score": r.score,
            "confidence": r.confidence,
        }

    insights = []

    for pattern in _WORK_STYLE_PATTERNS:
        required_keys = pattern["requires"]
        optional_keys = pattern.get("optional", [])
        threshold = pattern["threshold"]

        # Check if required competencies are available
        required_scores = []
        for key in required_keys:
            if key in score_lookup:
                required_scores.append(score_lookup[key])

        if not required_scores:
            continue

        # Also include optional scores if available
        optional_scores = []
        for key in optional_keys:
            if key in score_lookup:
                optional_scores.append(score_lookup[key])

        all_scores = required_scores + optional_scores

        # Compute average score and confidence
        avg_score = sum(s["score"] for s in all_scores) / len(all_scores)
        avg_confidence = sum(s["confidence"] for s in all_scores) / len(all_scores)

        # Determine strength level
        if avg_score >= threshold:
            strength = "strong"
            description = pattern["description_strong"]
        elif avg_score >= threshold * 0.6:
            strength = "moderate"
            description = pattern["description_moderate"]
        else:
            strength = "limited"
            description = (
                f"Limited interview evidence for {pattern['insight'].lower()}. "
                f"Further assessment may be needed."
            )

        insights.append({
            "insight": pattern["insight"],
            "strength": strength,
            "contributing_competencies": [
                {"name": s["name"], "score": s["score"]} for s in all_scores
            ],
            "description": description,
            "confidence": round(avg_confidence, 3),
            "disclaimer": WORK_STYLE_DISCLAIMER,
        })

    return insights
