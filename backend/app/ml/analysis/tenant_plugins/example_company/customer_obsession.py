"""
Customer Obsession — Example tenant-specific competency plugin.

This demonstrates how a company can add proprietary competencies
without modifying the platform.  This plugin:

  - Declares its preprocessing dependencies
  - Consumes only the ReadonlySessionContext
  - Returns an EnhancedMetricResult
  - Is completely isolated from core plugins
  - Fails safely

Usage:
  This plugin is auto-discovered when the company's analysis runs.
  The company_id in the config determines which tenant plugins load.
"""

from app.ml.analysis.interfaces import (
    EnhancedMetricResult,
    SessionContext,
    score_to_level,
)
from app.ml.analysis.scoring_utils import (
    evidence_based_confidence,
)
from app.ml.analysis.registry import register_tenant_metric


class CustomerObsessionMetric:
    """
    Evaluates customer obsession based on interview evidence.

    This is an EXAMPLE tenant plugin.  A real company plugin would
    contain proprietary evaluation logic that never appears in the
    platform source code.
    """
    name = "Customer Obsession"
    description = "Evaluates customer-centric thinking and behaviours"
    version = "1.0"
    author = "Example Company"
    supported_engine = 2
    requires = {"behaviour_evidence": 1}
    plugin_metadata = {
        "category": "competency",
        "tier": "tenant",
        "company": "example_company",
    }

    def compute(self, ctx: SessionContext) -> EnhancedMetricResult:
        """
        Score customer obsession based on extracted behaviour evidence.

        Looks for behaviours related to customer_focus, empathy,
        accountability, and problem_solving.
        """
        evidence = getattr(ctx, "evidence", None)

        if not evidence or evidence.is_empty():
            return EnhancedMetricResult(
                name=self.name,
                score=0,
                raw_score=0,
                level="Unavailable",
                confidence=0.0,
                summary="Insufficient evidence for customer obsession assessment.",
                reasoning="No structured evidence was available from the interview.",
                metadata=self.plugin_metadata,
            )

        # Find relevant behaviour evidence
        customer_behaviours = evidence.get_behaviours_by_type("customer_focus")
        empathy_behaviours = evidence.get_behaviours_by_type("collaboration")
        problem_solving = evidence.get_behaviours_by_type("problem_solving")

        all_relevant = customer_behaviours + empathy_behaviours + problem_solving

        if not all_relevant:
            return EnhancedMetricResult(
                name=self.name,
                score=30,
                raw_score=30,
                level=score_to_level(30),
                confidence=0.2,
                summary="Limited customer obsession indicators observed.",
                reasoning=(
                    "The interview did not contain strong indicators of "
                    "customer-centric thinking or behaviours."
                ),
                metadata=self.plugin_metadata,
            )

        # Score based on evidence quantity and quality
        avg_confidence = sum(b.confidence for b in all_relevant) / len(all_relevant)
        base_score = min(int(len(all_relevant) * 15 + avg_confidence * 30), 100)

        confidence = evidence_based_confidence(all_relevant)

        evidence_ids = [b.id for b in all_relevant]
        transcript_refs = [b.transcript_reference for b in all_relevant if b.transcript_reference]

        return EnhancedMetricResult(
            name=self.name,
            score=base_score,
            raw_score=base_score,
            level=score_to_level(base_score),
            confidence=confidence,
            summary=(
                f"Interview evidence suggests {'strong' if base_score >= 70 else 'moderate'} "
                f"customer-centric orientation based on {len(all_relevant)} observations."
            ),
            reasoning=(
                f"Found {len(customer_behaviours)} customer focus indicators, "
                f"{len(empathy_behaviours)} empathy indicators, and "
                f"{len(problem_solving)} problem-solving indicators."
            ),
            recommendations=[
                "Assess track record of customer advocacy in reference checks."
                if base_score >= 70 else
                "Probe deeper into customer interaction experiences in follow-up."
            ],
            transcript_references=transcript_refs[:5],
            evidence_ids=evidence_ids,
            metadata=self.plugin_metadata,
        )


# Register with the tenant registry (not the core registry)
register_tenant_metric("example_company", CustomerObsessionMetric())
