from __future__ import annotations

import re
from typing import Any

from app.agents.types import AgentResult
from app.services.runtime_store import RuntimeStore


class ApprovalAgent:
    agent_id = "A010"
    agent_name = "Approval Gateway Agent"

    def __init__(self, runtime_store: RuntimeStore):
        self.runtime_store = runtime_store

    def create(
        self,
        workflow_id: str,
        query: str,
        user: dict[str, Any],
        risk_tier: str,
        reassignment_plan: dict[str, Any] | None = None,
    ) -> tuple[dict[str, Any], AgentResult]:
        request_type, object_type, object_id, action, required_roles = self._classify(
            workflow_id, query, reassignment_plan
        )
        approval_payload: dict[str, Any] = {"query": query, "workflow_id": workflow_id}
        if reassignment_plan:
            approval_payload["reassignment_plan"] = reassignment_plan
        record = self.runtime_store.create_approval(
            request_type=request_type,
            business_object_type=object_type,
            business_object_id=object_id,
            requested_action=action,
            payload=approval_payload,
            risk_tier=risk_tier,
            required_roles=required_roles,
            requested_by=str(user["user_id"]),
        )
        result = AgentResult(
            self.agent_id,
            self.agent_name,
            f"Created pending approval {record['approval_id']} for {action.lower()}.",
            record,
            [
                {"source_id": "approval_policy", "title": "Approval Policies", "source_type": "Workflow rule", "path": "core/agents/workflow_definitions.csv"}
            ],
            1.0,
        )
        return record, result

    @staticmethod
    def _classify(
        workflow_id: str,
        query: str,
        reassignment_plan: dict[str, Any] | None = None,
    ) -> tuple[str, str, str, str, list[str]]:
        if workflow_id == "WFD005":
            task_id = str((reassignment_plan or {}).get("task_id", ""))
            if not re.fullmatch(r"T\d{5}", task_id):
                raise ValueError("A validated task ID is required for reassignment approval.")
            return "Task Reassignment", "task", task_id, "Reassign task", ["Project_Manager"]
        if workflow_id == "WFD007":
            order = re.search(r"\bSO\d{6}\b", query.upper())
            percent = re.search(r"(\d+(?:\.\d+)?)\s*%", query)
            roles = ["Finance_Manager", "Executive"] if percent and float(percent.group(1)) > 20 else ["Finance_Manager"]
            return "Sales Discount Exception", "sales_order", order.group(0) if order else "UNSPECIFIED_ORDER", "Approve discount", roles
        if workflow_id == "WFD008":
            purchase = re.search(r"\bPUR\d{4}\b", query.upper())
            return "Purchase Request", "purchase_request", purchase.group(0) if purchase else "UNSPECIFIED_PURCHASE", "Approve purchase", ["Finance_Manager"]
        if workflow_id == "WFD009":
            leave = re.search(r"\b(?:LV\d{5}|LR\d{3,5})\b", query.upper())
            return "Leave Request", "leave_request", leave.group(0) if leave else "UNSPECIFIED_LEAVE", "Approve leave", ["HR_Manager", "Project_Manager"]
        return "AI Human Review", "workflow", workflow_id, "Review AI response", ["AI_Reviewer"]
