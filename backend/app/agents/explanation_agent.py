from __future__ import annotations

from typing import Any

from app.agents.types import AgentResult


class ExplanationAgent:
    agent_id = "A009"
    agent_name = "Explanation Agent"

    def run(
        self,
        workflow: dict[str, Any],
        results: list[AgentResult],
        validation: dict[str, Any],
        plan: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], AgentResult]:
        trace = [
            {
                "agent_id": result.agent_id,
                "agent_name": result.agent_name,
                "contribution": result.summary,
                "confidence": round(result.confidence, 4),
            }
            for result in results
        ]
        evidence = []
        seen = set()
        for result in results:
            for source in result.sources:
                key = (source.get("source_id"), source.get("section"))
                if key in seen:
                    continue
                seen.add(key)
                evidence.append(source)
        explanation = {
            "workflow": workflow.get("workflow_name"),
            "risk_tier": workflow.get("risk_tier"),
            "why_this_route": f"The coordinator matched the request to {workflow.get('workflow_name')}.",
            "agent_contributions": trace,
            "evidence_count": len(evidence),
            "confidence_method": "Weighted router and agent confidence, with validation and grounding thresholds.",
            "human_review_rule": "Human approval is created only when the user's intent requests a sensitive action. Low-confidence read-only requests use a safe route without creating an approval.",
            "validation": validation,
        }
        if plan:
            explanation["routing_context"] = {
                key: plan.get(key)
                for key in (
                    "model_workflow_id",
                    "model_router_confidence",
                    "router_confidence_threshold",
                    "routing_reason",
                    "safe_fallback",
                    "attached_files",
                    "attachment_context_used",
                    "attachment_mode",
                    "retrieval_scope",
                    "detected_document_type",
                    "detected_domain",
                    "detected_project_id",
                    "detected_project_name",
                    "document_classification",
                    "declared_required_permission",
                    "backend_required_permission",
                    "sensitive_action_requested",
                    "reassignment_action_intent",
                    "reassignment_read_only_intent",
                )
            }
        scope_notes = [
            result.content.get("scope_explanation")
            for result in results
            if isinstance(result.content, dict) and result.content.get("scope_explanation")
        ]
        if scope_notes:
            explanation["data_scope"] = " ".join(scope_notes)
        result = AgentResult(
            self.agent_id,
            self.agent_name,
            "Generated an explainable trace linking the route, agents, evidence, confidence, and approval decision.",
            explanation,
            evidence,
            0.98,
        )
        return explanation, result
