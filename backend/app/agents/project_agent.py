from __future__ import annotations

from typing import Any

import pandas as pd

from app.agents.types import AgentResult
from app.ml.registry import ModelRegistry
from app.services.repository import DataRepository
from app.utils.json_tools import json_safe


class ProjectAgent:
    agent_id = "A005"
    agent_name = "Project Agent"

    def __init__(self, repository: DataRepository, models: ModelRegistry, snapshot_date: str):
        self.repository = repository
        self.models = models
        self.snapshot_date = pd.Timestamp(snapshot_date)

    def run(
        self, query: str, project_context: dict[str, Any] | None = None
    ) -> AgentResult:
        context = dict(project_context or self.repository.resolve_project_context(query))
        if context.get("requested") and not context.get("found"):
            requested_name = str(context.get("requested_name") or "requested project")
            return AgentResult(
                self.agent_id,
                self.agent_name,
                f"Project '{requested_name}' was not found.",
                {"project_found": False, "project_context": context},
                self._sources(),
                0.98,
                ["No project data or employee data was returned."],
            )

        project = None
        if context.get("found") and context.get("project_id"):
            projects = self.repository.table("projects")
            match = projects[projects["project_id"] == context["project_id"]]
            if not match.empty:
                project = json_safe(match.iloc[0].to_dict())
        elif not context.get("requested"):
            project = self.repository.find_project(query)
        if not project:
            projects = self.repository.table("projects").copy()
            portfolio = projects[
                [
                    "project_id",
                    "project_name",
                    "current_status",
                    "priority",
                    "current_progress_percent",
                    "expected_progress_percent",
                    "risk_level",
                    "planned_end_date",
                ]
            ].sort_values(["risk_level", "priority"], ascending=[False, True])
            return AgentResult(
                self.agent_id,
                self.agent_name,
                "No single project was identified; returned the enterprise project portfolio.",
                {
                    "project_count": int(len(projects)),
                    "at_risk_count": int((projects["current_status"] == "At Risk").sum()),
                    "projects": json_safe(portfolio.to_dict(orient="records")),
                },
                self._sources(),
                0.84,
                ["Mention a project name such as Atlas or Nova for a detailed analysis."],
            )

        detail = self.repository.project_detail(str(project["project_id"]))
        if not detail:
            return AgentResult(
                self.agent_id,
                self.agent_name,
                "The requested project could not be loaded.",
                {},
                self._sources(),
                0.50,
                ["Project record missing."],
            )
        member_employee_ids = self.repository.project_member_ids(str(project["project_id"]))
        context = {
            "requested": True,
            "found": True,
            "project_id": str(project["project_id"]),
            "project_name": str(project["project_name"]),
            "requested_name": context.get("requested_name") or str(project["project_name"]),
            "member_employee_ids": member_employee_ids,
            "member_count": len(member_employee_ids),
        }
        tasks = pd.DataFrame(detail["tasks"])
        tasks["due_date_parsed"] = pd.to_datetime(tasks["due_date"], errors="coerce")
        unfinished = tasks["status"] != "Completed"
        overdue = tasks[unfinished & (tasks["due_date_parsed"] < self.snapshot_date)]
        blocked = tasks[tasks["status"] == "Blocked"]
        tasks["predicted_task_risk"] = self.models.predict_task_risk(tasks)
        high_risk = tasks[tasks["predicted_task_risk"] == "High"]

        members = pd.DataFrame(detail["members"])
        if not members.empty and "total_workload_percent" in members.columns:
            overloaded = members[
                pd.to_numeric(members["total_workload_percent"], errors="coerce").fillna(0) >= 100
            ].sort_values("total_workload_percent", ascending=False)
        else:
            overloaded = pd.DataFrame()

        top_risks = sorted(detail["risks"], key=lambda item: item.get("risk_score", 0), reverse=True)[:5]
        progress_gap = float(project["expected_progress_percent"]) - float(
            project["current_progress_percent"]
        )
        content = {
            "project_context": context,
            "project": project,
            "progress_gap_percent": round(progress_gap, 2),
            "task_metrics": {
                "total": int(len(tasks)),
                "completed": int((tasks["status"] == "Completed").sum()),
                "unfinished": int(unfinished.sum()),
                "overdue_unfinished": int(len(overdue)),
                "blocked": int(len(blocked)),
                "model_high_risk_tasks": int(len(high_risk)),
            },
            "overdue_tasks": json_safe(
                overdue[
                    ["task_id", "task_title", "priority", "status", "due_date", "progress_percent"]
                ].head(15).to_dict(orient="records")
            ),
            "blocked_tasks": json_safe(
                blocked[
                    ["task_id", "task_title", "priority", "blocked_reason", "progress_percent"]
                ].head(10).to_dict(orient="records")
            ),
            "overloaded_members": json_safe(
                overloaded[
                    [
                        "employee_id",
                        "full_name",
                        "job_title",
                        "total_workload_percent",
                        "open_task_count",
                        "overdue_task_count",
                    ]
                ].head(10).to_dict(orient="records")
                if not overloaded.empty
                else []
            ),
            "top_risks": top_risks,
            "recommendations": self._recommendations(project, overdue, blocked, overloaded),
        }
        summary = (
            f"{project['project_name']} is {project['current_status']} with "
            f"{project['current_progress_percent']}% current progress versus "
            f"{project['expected_progress_percent']}% expected, {len(overdue)} overdue unfinished "
            f"tasks, and {len(blocked)} blocked tasks."
        )
        warnings: list[str] = []
        if not member_employee_ids:
            summary += " No members are assigned to this project."
            warnings.append("The project has no active member assignments.")
        return AgentResult(
            self.agent_id,
            self.agent_name,
            summary,
            content,
            self._sources(),
            0.97,
            warnings,
        )

    @staticmethod
    def _recommendations(
        project: dict[str, Any],
        overdue: pd.DataFrame,
        blocked: pd.DataFrame,
        overloaded: pd.DataFrame,
    ) -> list[str]:
        recommendations: list[str] = []
        if len(blocked):
            recommendations.append("Escalate blocked-task dependencies and assign accountable owners.")
        if len(overdue):
            recommendations.append("Re-plan overdue critical tasks and review milestone impact.")
        if not overloaded.empty:
            recommendations.append("Redistribute work from employees above 100% workload through approval.")
        if float(project["current_progress_percent"]) < float(project["expected_progress_percent"]):
            recommendations.append("Create a recovery plan for the progress gap and review it weekly.")
        if not recommendations:
            recommendations.append("Continue normal monitoring and preserve the current delivery cadence.")
        return recommendations

    @staticmethod
    def _sources() -> list[dict[str, Any]]:
        return [
            {"source_id": "projects", "title": "projects.csv", "source_type": "CSV", "path": "core/projects/projects.csv"},
            {"source_id": "tasks", "title": "tasks.csv", "source_type": "CSV", "path": "core/projects/tasks.csv"},
            {"source_id": "project_risks", "title": "project_risks.csv", "source_type": "CSV", "path": "core/projects/project_risks.csv"},
            {"source_id": "project_members", "title": "project_members.csv", "source_type": "CSV", "path": "core/projects/project_members.csv"},
            {"source_id": "workload", "title": "employee_workload_snapshots.csv", "source_type": "CSV", "path": "core/hr/employee_workload_snapshots.csv"},
        ]
