"""
Evidence extractor — retrieves pre-computed evidence for a metric.

Looks up a metric by name in the session_summary.metrics[] array
and returns its evidence, explanation, and signals_used fields.

This module does NOT call any AI model — it just extracts structured
data that was already computed by the Phase 10 metric plugins.
"""

import logging

logger = logging.getLogger(__name__)


def extract_evidence_for_metric(
    metric_name: str,
    session_summary: dict,
) -> dict | None:
    """
    Find a metric in the session summary and return its evidence.

    Args:
        metric_name: metric name (case-insensitive fuzzy match)
        session_summary: the session_summary JSONB from the DB

    Returns:
        {
            "metric": dict,       # full metric result
            "evidence": list,     # evidence array
            "explanation": str,   # pre-computed explanation
            "signals_used": list, # signal names
            "score": int,
            "level": str,
        }
        or None if metric not found.
    """
    if not session_summary:
        return None

    metrics = session_summary.get("metrics", [])
    if not metrics:
        return None

    # Case-insensitive fuzzy search
    query = metric_name.lower().strip()
    match = None

    for m in metrics:
        name = m.get("name", "").lower()
        if name == query or query in name or name in query:
            match = m
            break

    if not match:
        # Try partial word match
        for m in metrics:
            name = m.get("name", "").lower()
            if any(word in name for word in query.split()):
                match = m
                break

    if not match:
        return None

    return {
        "metric": match,
        "evidence": match.get("evidence", []),
        "explanation": match.get("explanation", ""),
        "signals_used": match.get("signals_used", []),
        "score": match.get("score", 0),
        "level": match.get("level", "Unknown"),
    }


def get_all_metrics_summary(session_summary: dict) -> list[dict]:
    """
    Return a summary of all metrics for context building.

    Returns list of {name, score, level} for all metrics.
    """
    if not session_summary:
        return []

    return [
        {
            "name": m.get("name", "Unknown"),
            "score": m.get("score", 0),
            "level": m.get("level", "Unknown"),
        }
        for m in session_summary.get("metrics", [])
    ]
