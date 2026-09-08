from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.agents.types import AgentResult
from app.ml.registry import ModelRegistry
from app.services.repository import DataRepository
from app.utils.intent import is_reassignment_action, is_reassignment_topic
from app.utils.json_tools import json_safe


class HRAgent:
    agent_id = "A004"
    agent_name = "HR Agent"

    def __init__(self, repository: DataRepository, models: ModelRegistry):
        self.repository = repository
        self.models = models

    def run(
        self,
        query: str,
        user: dict[str, Any],
        project_context: dict[str, Any] | None = None,
    ) -> AgentResult:
        lowered = query.lower()
        employees = self.repository.table("employees").copy()

        if "salary" in lowered or "compensation" in lowered:
            target = self.repository.employee_lookup(query)
            if target:
                content = {
                    "employee_id": target["employee_id"],
                    "employee": target["full_name"],
                    "department": target["department_name"],
                    "monthly_salary_usd": target["monthly_salary_usd"],
                    "annual_salary_usd": target["annual_salary_usd"],
                    "classification": target["data_classification"],
                }
                summary = f"Retrieved authorized compensation data for {target['full_name']}."
            else:
                grouped = (
                    employees.groupby("department_name")["annual_salary_usd"]
                    .agg(["count", "mean", "median"])
                    .sort_values("mean", ascending=False)
                    .round(2)
                    .reset_index()
                )
                content = {"department_salary_summary": json_safe(grouped.head(10).to_dict(orient="records"))}
                summary = "Calculated authorized department-level compensation statistics."
            return AgentResult(
                self.agent_id,
                self.agent_name,
                summary,
                content,
                self._sources("employees.csv"),
                0.96,
            )

        if is_reassignment_topic(query) or any(
            term in lowered
            for term in (
                "overload",
                "workload",
                "capacity",
                "available",
                "team member",
                "team members",
                "task allocation",
                "reassign",
            )
        ):
            context = dict(project_context or {})
            project_scoped = bool(context.get("requested"))
            if project_scoped and not context.get("found"):
                requested_name = str(context.get("requested_name") or "requested project")
                return AgentResult(
                    self.agent_id,
                    self.agent_name,
                    f"Project '{requested_name}' was not found; no HR data was analyzed.",
                    {
                        "scope": "project",
                        "project_found": False,
                        "project_context": context,
                        "matching_employee_count": 0,
                        "employees": [],
                    },
                    self._project_workload_sources(),
                    0.98,
                )

            all_workload = self.repository.latest_workload()
            workload = all_workload.copy()
            member_ids = list(dict.fromkeys(context.get("member_employee_ids", [])))
            if project_scoped:
                workload = workload[workload["employee_id"].astype(str).isin(member_ids)].copy()
            workload["predicted_status"] = (
                self.models.predict_workload(workload) if not workload.empty else []
            )
            merged = workload.merge(
                employees[["employee_id", "full_name", "department_name", "job_title"]],
                on="employee_id",
                how="left",
            )
            if "overload" in lowered:
                condition = "overloaded"
                threshold = 100.0
                selected = merged[
                    pd.to_numeric(merged["total_workload_percent"], errors="coerce") >= threshold
                ].sort_values("total_workload_percent", ascending=False)
            elif any(
                signal in lowered
                for signal in (
                    "available",
                    "availability",
                    "capacity",
                    "suitable",
                    "eligible",
                    "can take",
                    "receive work",
                    "receive reassigned",
                )
            ):
                condition = "available"
                threshold = 60.0
                selected = merged[
                    pd.to_numeric(merged["total_workload_percent"], errors="coerce") < threshold
                ].sort_values("total_workload_percent")
            elif "workload" in lowered:
                condition = "high_or_overloaded"
                threshold = None
                selected = merged[
                    merged["predicted_status"].isin(["High", "Overloaded"])
                ].sort_values("total_workload_percent", ascending=False)
            else:
                condition = "project_members"
                threshold = None
                selected = merged.sort_values(["full_name", "employee_id"])
            project_name = context.get("project_name")
            scope_explanation = (
                f"HR Agent analyzed {len(merged)} members assigned to {project_name} "
                f"and found {len(selected)} {condition.replace('_', ' ')} members."
                if project_scoped
                else f"HR Agent analyzed the company-wide workforce and found {len(selected)} matching employees."
            )
            content = {
                "scope": "project" if project_scoped else "company",
                "project_id": context.get("project_id") if project_scoped else None,
                "project_name": project_name if project_scoped else None,
                "project_member_ids": member_ids if project_scoped else [],
                "analyzed_employee_count": int(len(merged)),
                "scope_explanation": scope_explanation,
                "workload_condition": condition,
                "workload_threshold_percent": threshold,
                "snapshot_date": (
                    str(workload["snapshot_date"].max().date()) if not workload.empty else None
                ),
                "matching_employee_count": int(len(selected)),
                "employees": json_safe(
                    selected[
                        [
                            "employee_id",
                            "full_name",
                            "department_name",
                            "job_title",
                            "total_workload_percent",
                            "open_task_count",
                            "overdue_task_count",
                            "predicted_status",
                        ]
                    ]
                    .head(20)
                    .to_dict(orient="records")
                ),
            }
            if is_reassignment_topic(query):
                target_text = query
                if is_reassignment_action(query):
                    target_text_match = re.search(
                        r"\bto\s+(.+?)(?:\s+after\b|[.,;]|$)",
                        query,
                        flags=re.IGNORECASE,
                    )
                    if target_text_match:
                        target_text = target_text_match.group(1)
                target_employee = self.repository.employee_lookup(target_text)
                if target_employee:
                    target_id = str(target_employee["employee_id"])
                    target_workload_rows = all_workload[
                        all_workload["employee_id"].astype(str) == target_id
                    ]
                    target_workload = (
                        float(target_workload_rows.iloc[0]["total_workload_percent"])
                        if not target_workload_rows.empty
                        else None
                    )
                    active = str(target_employee.get("employment_status", "")).lower() == "active"
                    available = target_workload is not None and target_workload < 60.0
                    target_details = {
                        "employee_id": target_id,
                        "full_name": target_employee["full_name"],
                        "employment_status": target_employee.get("employment_status"),
                        "total_workload_percent": target_workload,
                        "predicted_status": "Available" if available else "Not Available",
                        "is_project_member": target_id in member_ids,
                        "eligible": bool(active and available),
                        "eligibility_reason": (
                            "Target employee is active and below the 60% availability threshold."
                            if active and available
                            else (
                                "The target employee is not active."
                                if not active
                                else "The target employee is not in the available workload range."
                            )
                        ),
                    }
                    content["target_employee"] = target_details
            if project_scoped and not member_ids:
                summary = f"No members are assigned to {project_name}."
            elif project_scoped and condition == "overloaded" and selected.empty:
                summary = "No overloaded team members were found for this project."
            else:
                summary = scope_explanation
            return AgentResult(
                self.agent_id,
                self.agent_name,
                summary,
                content,
                (
                    self._project_workload_sources()
                    if project_scoped
                    else self._sources("employee_workload_snapshots.csv", "employees.csv")
                ),
                0.94,
            )

        if "overtime" in lowered:
            top = employees.sort_values("overtime_hours_ytd", ascending=False).head(15)
            by_department = (
                employees.groupby("department_name")["overtime_hours_ytd"]
                .agg(["mean", "sum", "max"])
                .sort_values("mean", ascending=False)
                .round(2)
                .reset_index()
            )
            content = {
                "top_employees": json_safe(
                    top[
                        [
                            "employee_id",
                            "full_name",
                            "department_name",
                            "overtime_hours_ytd",
                            "job_rating",
                        ]
                    ].to_dict(orient="records")
                ),
                "department_summary": json_safe(by_department.head(10).to_dict(orient="records")),
            }
            return AgentResult(
                self.agent_id,
                self.agent_name,
                "Analyzed year-to-date employee overtime and department concentration.",
                content,
                self._sources("employees.csv"),
                0.95,
            )

        if any(term in lowered for term in ("leave", "absence", "attendance")):
            leave = self.repository.table("leave_requests").copy()
            if "leave.read_all" not in set(user.get("permissions", [])):
                leave = leave[leave["employee_id"] == user["employee_id"]]
            counts = leave["status"].value_counts().to_dict() if "status" in leave.columns else {}
            content = {
                "scope": "all employees" if "leave.read_all" in set(user.get("permissions", [])) else "current user",
                "request_count": int(len(leave)),
                "status_counts": json_safe(counts),
                "recent_requests": json_safe(leave.tail(15).to_dict(orient="records")),
            }
            return AgentResult(
                self.agent_id,
                self.agent_name,
                "Analyzed leave requests within the user's authorized scope.",
                content,
                self._sources("leave_requests.csv"),
                0.93,
            )

        headcount = (
            employees.groupby("department_name")
            .agg(
                employee_count=("employee_id", "count"),
                average_job_rating=("job_rating", "mean"),
                average_overtime=("overtime_hours_ytd", "mean"),
            )
            .round(2)
            .sort_values("employee_count", ascending=False)
            .reset_index()
        )
        content = {
            "total_employees": int(len(employees)),
            "departments": json_safe(headcount.to_dict(orient="records")),
        }
        return AgentResult(
            self.agent_id,
            self.agent_name,
            "Prepared an enterprise headcount and workforce overview.",
            content,
            self._sources("employees.csv"),
            0.92,
        )

    @staticmethod
    def _sources(*files: str) -> list[dict[str, Any]]:
        return [
            {
                "source_id": file.replace(".csv", ""),
                "title": file,
                "source_type": "CSV",
                "path": f"core/hr/{file}",
            }
            for file in files
        ]

    @classmethod
    def _project_workload_sources(cls) -> list[dict[str, Any]]:
        return cls._sources("employee_workload_snapshots.csv", "employees.csv") + [
            {
                "source_id": "project_members",
                "title": "project_members.csv",
                "source_type": "CSV",
                "path": "core/projects/project_members.csv",
            }
        ]
