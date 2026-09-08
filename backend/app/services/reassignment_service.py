from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.ml.registry import ModelRegistry
from app.services.repository import DataRepository
from app.utils.json_tools import json_safe


class ReassignmentService:
    """Build deterministic, non-mutating task reassignment plans."""

    OVERLOADED_THRESHOLD = 100.0
    AVAILABLE_THRESHOLD = 60.0
    CLOSED_STATUSES = {"completed", "closed", "cancelled"}
    PRIORITY_ORDER = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}

    def __init__(
        self,
        repository: DataRepository,
        models: ModelRegistry,
        snapshot_date: str,
    ):
        self.repository = repository
        self.models = models
        self.snapshot_date = pd.Timestamp(snapshot_date)

    def prepare(
        self,
        *,
        query: str,
        project_context: dict[str, Any],
        hr_content: dict[str, Any],
    ) -> tuple[dict[str, Any] | None, str | None]:
        if project_context.get("requested") and not project_context.get("found"):
            return None, f"Project '{project_context.get('requested_name')}' was not found."
        project_id = project_context.get("project_id")
        if not project_id:
            return None, "A specific project or task ID is required for task reassignment."

        target = hr_content.get("target_employee")
        if not isinstance(target, dict) or not target.get("employee_id"):
            return None, "The target employee could not be resolved from the request."
        if str(target.get("employment_status", "")).lower() != "active":
            return None, "The target employee is not active and cannot receive a task."
        if not target.get("eligible", False):
            reason = target.get("eligibility_reason") or "The target employee is not eligible."
            return None, str(reason)

        tasks = self.repository.tasks_with_runtime_assignments()
        project_tasks = tasks[tasks["project_id"].astype(str) == str(project_id)].copy()
        if project_tasks.empty:
            return None, "No tasks were found for the selected project."

        workload = self.repository.latest_workload()
        workload_values = {
            str(row["employee_id"]): float(row["total_workload_percent"])
            for _, row in workload.iterrows()
        }
        employees = self.repository.table("employees")
        employee_names = {
            str(row["employee_id"]): str(row["full_name"])
            for _, row in employees.iterrows()
        }
        member_ids = set(map(str, project_context.get("member_employee_ids", [])))
        explicit_match = re.search(r"\bT\d{5}\b", query.upper())
        explicit_task = explicit_match.group(0) if explicit_match else None
        overload_required = explicit_task is None or "overload" in query.lower()

        if explicit_task:
            match = project_tasks[project_tasks["task_id"].astype(str) == explicit_task]
            if match.empty:
                task = self.repository.task_record(explicit_task)
                if task:
                    return None, f"Task {explicit_task} does not belong to the selected project."
                return None, f"Task {explicit_task} was not found."
            candidates = match.copy()
        else:
            overloaded_ids = {
                employee_id
                for employee_id in member_ids
                if workload_values.get(employee_id, 0.0) >= self.OVERLOADED_THRESHOLD
            }
            if not overloaded_ids:
                return None, "No overloaded source employees were found for this project."
            candidates = project_tasks[
                project_tasks["assigned_to_employee_id"].astype(str).isin(overloaded_ids)
            ].copy()

        candidates = candidates[
            ~candidates["status"].astype(str).str.lower().isin(self.CLOSED_STATUSES)
        ].copy()
        candidates = candidates[
            candidates["assigned_to_employee_id"].notna()
            & candidates["assigned_to_employee_id"].astype(str).ne("")
        ].copy()
        if candidates.empty:
            return None, "No eligible open task was found for reassignment."

        if explicit_task:
            source_id = str(candidates.iloc[0]["assigned_to_employee_id"])
            if overload_required and workload_values.get(source_id, 0.0) < self.OVERLOADED_THRESHOLD:
                return None, f"Task {explicit_task}'s current assignee is not overloaded."
        else:
            source_ids = candidates["assigned_to_employee_id"].astype(str)
            candidates = candidates[
                source_ids.map(workload_values).fillna(0.0) >= self.OVERLOADED_THRESHOLD
            ].copy()
            if candidates.empty:
                return None, "No eligible open task assigned to an overloaded employee was found."

        candidates["predicted_task_risk"] = self.models.predict_task_risk(candidates)
        candidates["_due"] = pd.to_datetime(candidates["due_date"], errors="coerce")
        candidates["_overdue"] = candidates["_due"] < self.snapshot_date
        candidates["_blocked_or_high_risk"] = (
            candidates["status"].astype(str).str.lower().eq("blocked")
            | candidates["predicted_task_risk"].astype(str).str.lower().eq("high")
        )
        candidates["_priority"] = (
            candidates["priority"].map(self.PRIORITY_ORDER).fillna(99)
        )
        candidates["_source_workload"] = (
            candidates["assigned_to_employee_id"].astype(str).map(workload_values).fillna(0.0)
        )
        candidates["_due"] = candidates["_due"].fillna(pd.Timestamp.max.normalize())
        selected = candidates.sort_values(
            [
                "_overdue",
                "_blocked_or_high_risk",
                "_priority",
                "_due",
                "_source_workload",
                "task_id",
            ],
            ascending=[False, False, True, True, False, True],
        ).iloc[0]

        source_id = str(selected["assigned_to_employee_id"])
        target_id = str(target["employee_id"])
        if target_id == source_id:
            return None, "The target employee is already the task's current assignee."

        project_rows = self.repository.table("projects")
        project_match = project_rows[
            project_rows["project_id"].astype(str) == str(project_id)
        ]
        if project_match.empty:
            return None, "The selected project no longer exists."
        project = project_match.iloc[0]
        source_workload = float(workload_values.get(source_id, 0.0))
        target_workload = float(target["total_workload_percent"])
        reason = (
            "Source employee is overloaded and target employee has available capacity."
            if source_workload >= self.OVERLOADED_THRESHOLD
            else "The explicitly requested task can be transferred to an active employee with available capacity."
        )
        plan = {
            "project_id": str(project_id),
            "project_name": str(project["project_name"]),
            "task_id": str(selected["task_id"]),
            "task_title": str(selected["task_title"]),
            "task_status": str(selected["status"]),
            "task_priority": str(selected["priority"]),
            "task_due_date": str(selected["due_date"]),
            "task_predicted_risk": str(selected["predicted_task_risk"]),
            "task_reassignable": True,
            "source_employee_id": source_id,
            "source_employee_name": employee_names.get(source_id, source_id),
            "source_workload_percent": source_workload,
            "source_is_project_member": source_id in member_ids,
            "source_overload_required": overload_required,
            "target_employee_id": target_id,
            "target_employee_name": str(target["full_name"]),
            "target_workload_percent": target_workload,
            "target_employment_status": str(target["employment_status"]),
            "target_is_project_member": target_id in member_ids,
            "target_project_membership_required": False,
            "target_eligible": bool(target["eligible"]),
            "availability_threshold_percent": self.AVAILABLE_THRESHOLD,
            "overloaded_threshold_percent": self.OVERLOADED_THRESHOLD,
            "explicit_task_requested": explicit_task is not None,
            "reason": reason,
            "risk_tier": "High",
            "requires_approval": True,
            "validation_status": "Pending",
            "selection_factors": {
                "overdue": bool(selected["_overdue"]),
                "blocked_or_high_risk": bool(selected["_blocked_or_high_risk"]),
                "priority_rank": int(selected["_priority"]),
                "source_workload_percent": source_workload,
            },
        }
        return json_safe(plan), None
