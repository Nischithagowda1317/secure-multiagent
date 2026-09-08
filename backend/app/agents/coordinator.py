from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from app.agents.types import AgentResult
from app.ml.registry import ModelRegistry
from app.services.repository import DataRepository
from app.utils.intent import (
    is_reassignment_action,
    is_reassignment_topic,
    reassignment_read_workflow,
)
from app.utils.text import tokenize


class CoordinatorAgent:
    agent_id = "A001"
    agent_name = "Coordinator Agent"

    def __init__(self, repository: DataRepository, models: ModelRegistry):
        self.repository = repository
        self.models = models

    def plan(
        self,
        query: str,
        attached_files: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], AgentResult]:
        attachments = attached_files or []
        model_workflow_id, model_confidence = self.models.route(query)
        threshold = self.models.settings.router_confidence_threshold
        document_context = self._document_context(query, attachments)
        strong_text_route = self._strong_text_route(query)
        reassignment_action = is_reassignment_action(query)
        reassignment_topic = is_reassignment_topic(query)
        sensitive_action = self._sensitive_action_requested(query)

        workflow_id = model_workflow_id
        confidence = model_confidence
        routing_reason = "router_model"
        safe_fallback = False

        # Explicit user actions and clearly stated business questions take
        # precedence over an unrelated attachment. These rules constrain the
        # ML router; they do not grant access to the selected resource.
        if sensitive_action:
            workflow_id = strong_text_route or model_workflow_id
            confidence = max(model_confidence, 0.90)
            routing_reason = "explicit_sensitive_action"
        elif reassignment_topic and not reassignment_action:
            workflow_id = reassignment_read_workflow(query)
            if workflow_id == "WFD003":
                confidence = max(model_confidence, 0.90)
                routing_reason = "read_only_reassignment_analysis"
            else:
                confidence = model_confidence
                routing_reason = "ambiguous_reassignment_safe_fallback"
                safe_fallback = True
        elif document_context["attachment_context_used"]:
            if document_context["detected_domain"] == "project" and self._requests_project_comparison_or_analysis(query):
                workflow_id = "WFD002"
                confidence = max(model_confidence, 0.90)
                routing_reason = "project_attachment_analysis"
            elif self._is_summary_request(query) or not query.strip():
                workflow_id = "WFD001"
                confidence = max(model_confidence, 0.85)
                routing_reason = "safe_document_analysis"
            elif document_context["retrieval_scope"] == "attachment_only":
                workflow_id = "WFD001"
                confidence = max(model_confidence, 0.85)
                routing_reason = "attachment_only_question"
            elif strong_text_route:
                workflow_id = strong_text_route
                confidence = max(model_confidence, 0.85)
                routing_reason = "explicit_text_intent_with_attachment"
            else:
                workflow_id = "WFD001"
                confidence = max(model_confidence, 0.80)
                routing_reason = "contextual_document_analysis"
        elif strong_text_route:
            workflow_id = strong_text_route
            confidence = max(model_confidence, 0.85)
            routing_reason = "explicit_text_intent"
        elif model_confidence < threshold:
            workflow_id = "WFD001"
            confidence = model_confidence
            routing_reason = "low_confidence_safe_fallback"
            safe_fallback = True

        workflow = self.repository.workflow_map.get(workflow_id)
        if not workflow:
            workflow_id = "WFD001"
            workflow = self.repository.workflow_map[workflow_id]
            routing_reason = "unknown_workflow_safe_fallback"
            safe_fallback = True

        project_query = query
        if document_context["attachment_context_used"] and document_context["detected_domain"] == "project":
            project_query = document_context["routing_text"]
        project_context = self.repository.resolve_project_context(project_query)
        backend_permission = None
        if (
            document_context["attachment_context_used"]
            and document_context["detected_domain"] == "project"
            and workflow_id in {"WFD001", "WFD002"}
        ):
            # This is a deterministic backend mapping. A permission string
            # written inside a document is retained only as untrusted metadata.
            backend_permission = "project.read"

        agents = str(workflow.get("required_agents", "")).split("|")
        plan = {
            "workflow_id": workflow_id,
            "workflow_name": workflow.get("workflow_name", workflow_id),
            "risk_tier": workflow.get("risk_tier", "Medium"),
            "required_agents": [agent for agent in agents if agent],
            "approval_condition": workflow.get("approval_condition", ""),
            "expected_output": workflow.get("expected_output", ""),
            "router_confidence": confidence,
            "model_workflow_id": model_workflow_id,
            "model_router_confidence": model_confidence,
            "router_confidence_threshold": threshold,
            "routing_reason": routing_reason,
            "safe_fallback": safe_fallback,
            "sensitive_action_requested": sensitive_action,
            "reassignment_action_intent": reassignment_action,
            "reassignment_read_only_intent": bool(
                reassignment_topic and not reassignment_action
            ),
            "project_context": project_context,
            "backend_required_permission": backend_permission,
            "attached_files": document_context["attached_files"],
            "attachment_context_used": document_context["attachment_context_used"],
            "attachment_mode": document_context["attachment_mode"],
            "retrieval_scope": document_context["retrieval_scope"],
            "detected_document_type": document_context["detected_document_type"],
            "detected_domain": document_context["detected_domain"],
            "detected_project_id": project_context.get("project_id"),
            "detected_project_name": project_context.get("project_name"),
            "document_classification": document_context["document_classification"],
            "declared_required_permission": document_context["declared_required_permission"],
        }
        project_context = plan["project_context"]
        scope_note = ""
        if project_context["requested"]:
            scope_note = (
                f" Project scope resolved to {project_context['project_name']} "
                f"({project_context['project_id']})."
                if project_context["found"]
                else f" Project reference '{project_context['requested_name']}' was not found."
            )
        result = AgentResult(
            agent_id=self.agent_id,
            agent_name=self.agent_name,
            summary=(
                f"Classified the request as {plan['workflow_name']} using {routing_reason.replace('_', ' ')}."
                f"{scope_note}"
            ),
            content=plan,
            sources=[
                {
                    "source_id": "workflow_definitions",
                    "title": "Workflow Definitions",
                    "source_type": "CSV",
                    "path": "core/agents/workflow_definitions.csv",
                }
            ],
            confidence=confidence,
        )
        return plan, result

    def _document_context(
        self, query: str, attachments: list[dict[str, Any]]
    ) -> dict[str, Any]:
        if not attachments:
            return {
                "attached_files": [],
                "attachment_context_used": False,
                "attachment_mode": None,
                "retrieval_scope": "enterprise_only",
                "detected_document_type": None,
                "detected_domain": None,
                "document_classification": None,
                "declared_required_permission": None,
                "routing_text": query,
            }

        filenames = " ".join(str(item.get("filename", "")) for item in attachments)
        extracted_text = "\n".join(
            str(item.get("extracted_text", ""))[:20_000] for item in attachments
        )
        routing_text = "\n".join((query, filenames, extracted_text))
        normalized = routing_text.lower().replace("_", " ").replace("-", " ")

        project_signals = (
            "project ",
            "project atlas",
            "current progress",
            "expected progress",
            "project manager",
            "overdue unfinished task",
            "blocked task",
            "milestone",
        )
        leave_signals = ("leave balance", "leave request", "attendance", "absence")
        project_score = sum(signal in normalized for signal in project_signals)
        leave_score = sum(signal in normalized for signal in leave_signals)
        if project_score >= 2 and project_score > leave_score:
            domain = "project"
            document_type = "project_status_report" if "status report" in normalized else "project_document"
        elif leave_score >= 2 and leave_score > project_score:
            domain = "leave"
            document_type = "leave_document"
        elif "policy" in normalized:
            domain = "policy"
            document_type = "policy_document"
        else:
            domain = "general"
            document_type = self._generic_document_type(attachments)

        explicit_reference = self._references_attachment(query)
        semantic_match = self._semantic_attachment_match(query, extracted_text, filenames)
        use_attachment = not query.strip() or explicit_reference or semantic_match
        summary_request = not query.strip() or self._is_attachment_summary_request(query)
        external_comparison = self._requests_external_attachment_comparison(query)
        project_analysis = (
            domain == "project"
            and self._requests_project_comparison_or_analysis(query)
        )
        if not use_attachment:
            attachment_mode = None
            retrieval_scope = "enterprise_only"
        elif external_comparison or project_analysis:
            attachment_mode = "compare"
            retrieval_scope = "attachment_plus_enterprise"
        elif summary_request:
            attachment_mode = "summary"
            retrieval_scope = "attachment_only"
        else:
            attachment_mode = "question"
            retrieval_scope = "attachment_only"

        classification_match = re.search(
            r"\bclassification\s*(?:[:|]|\r?\n)\s*(public|internal|confidential|restricted)\b",
            extracted_text,
            re.IGNORECASE,
        )
        permission_match = re.search(
            r"\brequired\s+permission\s*(?:[:|]|\r?\n)\s*([a-z][a-z0-9_.-]+)",
            extracted_text,
            re.IGNORECASE,
        )
        safe_files = [
            {
                "filename": str(item.get("filename", "attachment")),
                "content_type": str(item.get("content_type", "application/octet-stream")),
                "size_bytes": int(item.get("size_bytes", 0)),
                "chunk_count": int(item.get("chunk_count", 0)),
                "extracted_character_count": len(str(item.get("extracted_text", ""))),
            }
            for item in attachments
        ]
        return {
            "attached_files": safe_files,
            "attachment_context_used": use_attachment,
            "attachment_mode": attachment_mode,
            "retrieval_scope": retrieval_scope,
            "detected_document_type": document_type,
            "detected_domain": domain,
            "document_classification": (
                classification_match.group(1).title() if classification_match else None
            ),
            "declared_required_permission": (
                permission_match.group(1).lower() if permission_match else None
            ),
            "routing_text": routing_text if use_attachment else query,
        }

    @staticmethod
    def _generic_document_type(attachments: list[dict[str, Any]]) -> str:
        suffixes = {Path(str(item.get("filename", ""))).suffix.lower() for item in attachments}
        if len(suffixes) == 1:
            suffix = next(iter(suffixes)).lstrip(".")
            return f"{suffix}_document" if suffix else "document"
        return "document_collection"

    @staticmethod
    def _references_attachment(query: str) -> bool:
        lowered = query.lower()
        return bool(
            re.search(r"\b(this|these|the|my|attached|uploaded)\s+(?:word\s+)?(document|documents|file|files|pdf|pdfs|report|reports|spreadsheet|spreadsheets|attachment|attachments|policy)\b", lowered)
            or re.search(r"\b(summarize|summarise|analyse|analyze|review)\s+(?:me\s+)?(this|these|the|my|attached|uploaded)\b", lowered)
            or ("compare" in lowered and any(term in lowered for term in ("report", "document", "file", "pdf")))
        )

    @staticmethod
    def _semantic_attachment_match(query: str, text: str, filenames: str) -> bool:
        ignored = {
            "about", "after", "against", "current", "from", "have", "information",
            "please", "policy", "report", "show", "that", "their", "this", "what",
            "when", "where", "which", "with", "work", "would",
        }
        query_terms = {term for term in tokenize(query) if len(term) >= 4 and term not in ignored}
        if not query_terms:
            return False
        attachment_terms = set(tokenize(f"{filenames} {text}"))
        overlap = query_terms.intersection(attachment_terms)
        return len(overlap) >= 2 or len(overlap) / len(query_terms) >= 0.67

    @staticmethod
    def _is_summary_request(query: str) -> bool:
        return bool(re.search(r"\b(summarize|summarise|summary|synopsis|key points)\b", query.lower()))

    @staticmethod
    def _is_attachment_summary_request(query: str) -> bool:
        lowered = query.lower()
        return bool(
            CoordinatorAgent._is_summary_request(query)
            or re.search(r"\bwhat\s+does\s+(?:this|the|attached|uploaded)\s+(?:document|file|pdf|report)\s+say\b", lowered)
            or re.search(r"\btell\s+me\s+what\s+(?:this|the|attached|uploaded)\s+(?:document|file|pdf|report)\s+says\b", lowered)
            or re.search(r"\bgive\s+me\s+(?:the\s+)?key\s+points\b", lowered)
        )

    @staticmethod
    def _requests_external_attachment_comparison(query: str) -> bool:
        lowered = query.lower()
        return bool(
            re.search(r"\b(compare|contrast|reconcile|validate)\b", lowered)
            and re.search(
                r"\b(current|database|enterprise|knowledge|our|policy|policies|rules|project|records|data)\b",
                lowered,
            )
        )

    @staticmethod
    def _requests_project_comparison_or_analysis(query: str) -> bool:
        lowered = query.lower()
        return bool(
            re.search(r"\b(analyse|analyze|compare|assess|review|risk|status)\b", lowered)
            and not CoordinatorAgent._is_summary_request(query)
        )

    @staticmethod
    def _strong_text_route(query: str) -> str | None:
        lowered = query.lower()
        if not lowered.strip():
            return None
        if "salary" in lowered or "compensation" in lowered:
            return "WFD004"
        if is_reassignment_action(query):
            return "WFD005"
        if "discount" in lowered and any(word in lowered for word in ("approve", "apply", "authorize", "exception", "%")):
            return "WFD007"
        if "purchase" in lowered and any(word in lowered for word in ("approve", "authorize", "approval", "request")):
            return "WFD008"
        if any(word in lowered for word in ("leave", "attendance", "absence")):
            return "WFD009"
        if any(word in lowered for word in ("agent reliability", "hallucination", "grounding", "pass rate")):
            return "WFD011"
        if any(word in lowered for word in ("workload", "overloaded", "team member")) or (
            "employee" in lowered and any(word in lowered for word in ("capacity", "available"))
        ):
            return "WFD003"
        if "project" in lowered or re.search(r"\bPRJ\d{3}\b", query.upper()):
            if any(word in lowered for word in ("workload", "overloaded", "employee", "team member")):
                return "WFD003"
            return "WFD002"
        if any(word in lowered for word in ("sales", "profit", "revenue", "product", "region", "channel")):
            return "WFD006"
        if any(word in lowered for word in ("restricted", "confidential", "security policy")):
            return "WFD010"
        return None

    @staticmethod
    def _sensitive_action_requested(query: str) -> bool:
        if is_reassignment_action(query):
            return True
        lowered = query.lower()
        action = re.search(r"\b(approve|authorize|reject|apply|execute)\b", lowered)
        sensitive_object = re.search(r"\b(leave|purchase|discount|sales order)\b", lowered)
        return bool(action and sensitive_object)
