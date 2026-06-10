"""
Context builder — constructs Ollama prompts for explainable AI.

Builds prompts that include ONLY pre-computed evidence from the
metric plugins. This prevents the LLM from hallucinating evidence —
it can only explain what the system actually observed.

Follows the same Ollama integration pattern as question_generator.py.
"""

import logging

from app.ml.explain.evidence_extractor import (
    extract_evidence_for_metric,
    get_all_metrics_summary,
)

logger = logging.getLogger(__name__)


def build_explanation_context(
    question: str,
    session_summary: dict,
    transcript_excerpt: str = "",
) -> dict:
    """
    Build the context needed for an explanation.

    Identifies the most relevant metric based on the question,
    and constructs a prompt that constrains the LLM to the evidence.

    Returns:
        {
            "prompt": str,         # ready for Ollama
            "metric_name": str,    # matched metric
            "has_evidence": bool,
        }
    """
    # Try to identify which metric the question is about
    metric_keywords = _extract_metric_keywords(question)
    matched_metric = None

    for keyword in metric_keywords:
        result = extract_evidence_for_metric(keyword, session_summary)
        if result:
            matched_metric = result
            break

    # Get overview of all metrics for general questions
    all_metrics = get_all_metrics_summary(session_summary)
    metrics_overview = "\n".join(
        f"- {m['name']}: {m['score']}/100 ({m['level']})"
        for m in all_metrics
    )

    if matched_metric:
        # Specific metric question — constrain to its evidence
        evidence_text = ""
        for e in matched_metric["evidence"]:
            quote = e.get("quote", "")
            source = e.get("source", "")
            if quote:
                evidence_text += f'- "{quote}" (source: {source})\n'

        prompt = f"""You are an AI interview analysis assistant. A recruiter is asking about a candidate's interview performance.

METRIC: {matched_metric['metric'].get('name', 'Unknown')}
SCORE: {matched_metric['score']}/100
LEVEL: {matched_metric['level']}
EXPLANATION: {matched_metric['explanation']}

EVIDENCE (these are the ONLY observations you may reference):
{evidence_text if evidence_text else '- No specific evidence quotes available'}

SIGNALS USED: {', '.join(matched_metric['signals_used']) if matched_metric['signals_used'] else 'N/A'}

{f'TRANSCRIPT EXCERPT: {transcript_excerpt[:500]}' if transcript_excerpt else ''}

RECRUITER QUESTION: {question}

RULES:
- Answer ONLY based on the evidence and signals listed above.
- Do NOT invent or hallucinate any quotes, behaviors, or observations.
- If the evidence does not support a clear answer, say so honestly.
- Be concise and professional.
- Respond in 2-4 sentences.

ANSWER:"""

        return {
            "prompt": prompt,
            "metric_name": matched_metric["metric"].get("name", "Unknown"),
            "has_evidence": bool(matched_metric["evidence"]),
        }

    else:
        # General question — provide overview
        prompt = f"""You are an AI interview analysis assistant. A recruiter is asking about a candidate's interview performance.

METRICS OVERVIEW:
{metrics_overview if metrics_overview else 'No metrics have been computed yet.'}

{f'TRANSCRIPT EXCERPT: {transcript_excerpt[:500]}' if transcript_excerpt else ''}

RECRUITER QUESTION: {question}

RULES:
- Answer based ONLY on the metric scores and levels listed above.
- Do NOT invent specific quotes or behaviors.
- Be concise and professional.
- If you cannot answer from the available data, say so honestly.
- Respond in 2-4 sentences.

ANSWER:"""

        return {
            "prompt": prompt,
            "metric_name": "overview",
            "has_evidence": False,
        }


def _extract_metric_keywords(question: str) -> list[str]:
    """
    Extract potential metric names from the recruiter's question.

    E.g., "Why was confidence high?" → ["confidence"]
    E.g., "What evidence supports leadership?" → ["leadership"]
    """
    question_lower = question.lower()

    # Known metric names to look for
    known_metrics = [
        "confidence", "engagement", "stress", "attention",
        "communication", "emotional stability", "stability",
        "leadership", "teamwork", "adaptability",
    ]

    found = []
    for metric in known_metrics:
        if metric in question_lower:
            found.append(metric)

    # If no known metric found, try extracting key nouns
    if not found:
        # Fallback: use words after "about", "for", "of"
        import re
        patterns = [
            r"(?:about|for|of|regarding)\s+(\w+)",
            r"(\w+)\s+(?:score|level|metric|rating)",
            r"why\s+(?:was|is|were)\s+(\w+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, question_lower)
            if match:
                found.append(match.group(1))

    return found if found else [question_lower.split()[-1]]  # last word as fallback
