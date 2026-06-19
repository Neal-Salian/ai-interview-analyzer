import logging
from typing import Dict, Any
from app.db.crud import get_evaluation_feedbacks_by_category

from .domain_detector import detect_domain, get_evaluation_rubric
from .rule_evaluator import evaluate_rules
from .llm_evaluator import evaluate_llm
from .knowledge_validator import validate_knowledge

logger = logging.getLogger(__name__)

async def calculate_adaptive_weights(category: str) -> tuple[float, float]:
    """
    Adaptive Weight Learning:
    Reads recruiter feedback history to adjust rule vs LLM weights.
    Base weights are 0.3 (Rule) and 0.7 (LLM).
    If recruiters frequently agree, LLM weight increases.
    If recruiters frequently disagree, Rule weight increases.
    """
    base_rule_weight = 0.3
    base_llm_weight = 0.7
    
    feedbacks = get_evaluation_feedbacks_by_category(category)
    if not feedbacks:
        return base_rule_weight, base_llm_weight
        
    total = len(feedbacks)
    agrees = sum(1 for f in feedbacks if f.decision.lower() == 'agree')
    disagrees = total - agrees
    
    # Simple heuristic: for every 10% more disagrees than agrees, shift 0.05 weight to Rules.
    # Max shift is 0.2
    disagree_ratio = disagrees / total
    shift = min((disagree_ratio - 0.5) * 0.5, 0.2)
    
    if shift > 0:
        rule_weight = min(base_rule_weight + shift, 0.8)
        llm_weight = 1.0 - rule_weight
    else:
        llm_weight = min(base_llm_weight - shift, 0.9)
        rule_weight = 1.0 - llm_weight
        
    return round(rule_weight, 2), round(llm_weight, 2)


async def evaluate_answer(
    transcript: str, 
    job_title: str, 
    job_description: str,
    category: str = "domain_knowledge"
) -> Dict[str, Any]:
    """
    Main entry point for Domain-Aware Evaluation.
    Combines Domain Detection, Rule Evaluation, LLM Evaluation, and Knowledge Validation.
    """
    domain = detect_domain(job_title, job_description)
    rubric = get_evaluation_rubric(domain)
    
    rule_score = evaluate_rules(transcript, domain, rubric)
    
    llm_result = await evaluate_llm(transcript, domain, rubric)
    knowledge_result = await validate_knowledge(transcript, domain, rubric)
    
    rule_weight, llm_weight = await calculate_adaptive_weights(category)
    
    combined_score = (rule_score * rule_weight) + (llm_result["score"] * llm_weight)
    
    # Identify evidence from transcript
    # In a more advanced implementation, this would extract exact quotes.
    # For now, we take a snippet.
    evidence = [transcript[:150] + "..."] if len(transcript) > 150 else [transcript]
    
    return {
        "category": category,
        "domain": domain,
        "rule_score": round(rule_score, 2),
        "llm_score": round(llm_result["score"], 2),
        "combined_score": round(combined_score, 2),
        "strengths": llm_result["strengths"],
        "improvement_areas": llm_result["improvement_areas"],
        "overall_assessment": llm_result["overall_assessment"],
        "correct_concepts": knowledge_result["correct_concepts"],
        "missing_concepts": knowledge_result["missing_concepts"],
        "potential_inaccuracies": knowledge_result["potential_inaccuracies"],
        "confidence_level": knowledge_result["confidence_level"],
        "evidence": evidence
    }
