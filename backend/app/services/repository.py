from __future__ import annotations

import difflib
import re
from datetime import date, datetime
from functools import cached_property
from pathlib import Path
from typing import Any

import pandas as pd

from app.settings import Settings
from app.utils.json_tools import json_safe
from app.utils.text import normalize_text, pipe_values


class DataRepository:
    """Read-only access to enterprise tables in CSV or PostgreSQL.

    The dataset is intentionally small enough for an academic prototype, so the
    service loads tables lazily into pandas and keeps them in memory. Runtime
    writes such as approvals, uploads, and audit events are stored separately in
    SQLite or PostgreSQL by RuntimeStore.
    """

    TABLES: dict[str, str] = {
        "users": "core/identity_access/users.csv",
        "roles": "core/identity_access/roles.csv",
        "permissions": "core/identity_access/permissions.csv",
        "user_roles": "core/identity_access/user_roles.csv",
        "role_permissions": "core/identity_access/role_permissions.csv",
        "demo_credentials": "core/identity_access/demo_credentials.csv",
        "departments": "core/identity_access/departments.csv",
        "employees": "core/hr/employees.csv",
        "employee_skills": "core/hr/employee_skills.csv",
        "workload": "core/hr/employee_workload_snapshots.csv",
        "attendance": "core/hr/attendance_summary.csv",
        "leave_requests": "core/hr/leave_requests.csv",
        "projects": "core/projects/projects.csv",
        "project_members": "core/projects/project_members.csv",
        "tasks": "core/projects/tasks.csv",
        "task_dependencies": "core/projects/task_dependencies.csv",
        "project_risks": "core/projects/project_risks.csv",
        "customers": "core/sales_finance/customers.csv",
        "products": "core/sales_finance/products.csv",
        "sales_orders": "core/sales_finance/sales_orders.csv",
        "sales_targets": "core/sales_finance/sales_targets.csv",
        "suppliers": "core/sales_finance/suppliers.csv",
        "purchase_requests": "core/sales_finance/purchase_requests.csv",
        "expense_claims": "core/sales_finance/expense_claims.csv",
        "agent_registry": "core/agents/agent_registry.csv",
        "tool_registry": "core/agents/tool_registry.csv",
        "workflow_definitions": "core/agents/workflow_definitions.csv",
        "workflow_runs": "core/agents/workflow_runs.csv",
        "agent_logs": "core/agents/agent_execution_logs.csv",
        "approval_requests": "core/security_audit/approval_requests.csv",
        "approval_actions": "core/security_audit/approval_actions.csv",
        "access_decisions": "core/security_audit/access_control_decisions.csv",
        "audit_logs": "core/security_audit/audit_logs.csv",
        "document_catalog": "core/rag/document_catalog.csv",
        "rag_chunks": "core/rag/rag_chunks.csv",
        "rag_questions": "core/rag/rag_evaluation_questions.csv",
        "prompt_injection_tests": "core/rag/prompt_injection_tests.csv",
        "daily_metrics": "core/evaluation/daily_evaluation_metrics.csv",
        "evaluation_programs": "core/evaluation/evaluation_programs.csv",
        "evaluation_runs": "core/evaluation/evaluation_runs.csv",
        "evaluation_items": "core/evaluation/evaluation_items.csv",
        "judge_results": "core/evaluation/judge_results.csv",
        "reviewer_decisions": "core/evaluation/reviewer_decisions.csv",
        "routing_tests": "core/evaluation/routing_test_cases.csv",
        "workflow_tests": "core/evaluation/workflow_test_cases.csv",
        "security_tests": "core/evaluation/security_test_cases.csv",
        "explainability_tests": "core/evaluation/explainability_test_cases.csv",
        "agent_performance_summary": "core/evaluation/agent_performance_summary.csv",
        "agent_performance_source": "raw_sources/agentic_ai_performance_source.csv",
    }

    def __init__(self, settings: Settings, runtime_store: Any | None = None):
        self.settings = settings
        self.runtime_store = runtime_store
        self.root = settings.dataset_root
        self._cache: dict[str, pd.DataFrame] = {}
        self._engine: Any | None = None
        if self.settings.data_backend == "csv" and not self.root.exists():
            raise FileNotFoundError(f"Dataset root does not exist: {self.root}")
        if self.settings.uses_postgres:
            try:
                from app.services.postgres import create_postgres_engine, validate_schema
                validate_schema(self.settings.database_schema)
                self._engine = create_postgres_engine(self.settings.database_url)
            except ImportError as exc:
                raise RuntimeError(
                    "PostgreSQL support requires SQLAlchemy and psycopg. "
                    "Install backend/requirements.txt first."
                ) from exc
        elif self.settings.data_backend != "csv":
            raise ValueError(
                f"Unsupported DATA_BACKEND={self.settings.data_backend!r}. Use 'csv', 'postgres', or 'supabase'."
            )

    def table(self, name: str) -> pd.DataFrame:
        if name not in self.TABLES:
            raise KeyError(f"Unknown table: {name}")
        if name not in self._cache:
            relative = self.TABLES[name]
            if self.settings.uses_postgres:
                assert self._engine is not None
                table_name = Path(relative).stem
                try:
                    from sqlalchemy import text

                    # Both identifiers come from validated configuration and
                    # our fixed TABLES map, never from a user's query. Avoid
                    # read_sql_table's many schema-reflection round trips.
                    frame = pd.read_sql_query(
                        text(f'SELECT * FROM "{self.settings.database_schema}"."{table_name}"'),
                        con=self._engine,
                    )
                    # Preserve read_sql_table's date normalization without
                    # querying PostgreSQL's system catalogs for type metadata.
                    for column in frame.columns:
                        if not pd.api.types.is_object_dtype(frame[column].dtype):
                            continue
                        values = frame[column].dropna()
                        if not values.empty and isinstance(values.iloc[0], (date, datetime)):
                            frame[column] = pd.to_datetime(frame[column])
                    self._cache[name] = frame
                except Exception as exc:
                    raise RuntimeError(
                        f"Could not read PostgreSQL table "
                        f"{self.settings.database_schema}.{table_name}. "
                        "Apply the Supabase migration and run backend/scripts/load_supabase.py "
                        "(or load_postgresql.py for the legacy local setup)."
                    ) from exc
            else:
                path = self.root / relative
                self._cache[name] = pd.read_csv(path, encoding="utf-8-sig")
        return self._cache[name]

    @cached_property
    def role_permission_map(self) -> dict[str, set[str]]:
        frame = self.table("role_permissions")
        mapping: dict[str, set[str]] = {}
        for role, group in frame.groupby("role_name"):
            mapping[str(role)] = set(group["permission_name"].astype(str))
        return mapping

    @cached_property
    def workflow_map(self) -> dict[str, dict[str, Any]]:
        frame = self.table("workflow_definitions")
        return {
            str(row["workflow_definition_id"]): json_safe(row.to_dict())
            for _, row in frame.iterrows()
        }

    @cached_property
    def agent_map(self) -> dict[str, dict[str, Any]]:
        frame = self.table("agent_registry")
        return {
            str(row["agent_id"]): json_safe(row.to_dict())
            for _, row in frame.iterrows()
        }

    def user_record(self, email: str) -> dict[str, Any] | None:
        users = self.table("users")
        match = users[users["email"].str.lower() == email.strip().lower()]
        if match.empty:
            return None
        return json_safe(match.iloc[0].to_dict())

    def user_record_by_id(self, user_id: str) -> dict[str, Any] | None:
        users = self.table("users")
        match = users[users["user_id"] == user_id]
        if match.empty:
            return None
        return json_safe(match.iloc[0].to_dict())

    def user_context(self, user_id: str) -> dict[str, Any] | None:
        user = self.user_record_by_id(user_id)
        if not user:
            return None
        employee = self.table("employees")
        emp_match = employee[employee["employee_id"] == user["employee_id"]]
        emp = json_safe(emp_match.iloc[0].to_dict()) if not emp_match.empty else {}
        role_rows = self.table("user_roles")
        roles = sorted(
            role_rows.loc[role_rows["user_id"] == user_id, "role_name"].astype(str).tolist()
        )
        permissions: set[str] = set()
        for role in roles:
            permissions.update(self.role_permission_map.get(role, set()))
        return {
            **user,
            "full_name": emp.get("full_name", user.get("username", "User")),
            "department_name": emp.get("department_name"),
            "job_title": emp.get("job_title"),
            "roles": roles,
            "permissions": sorted(permissions),
        }

    def demo_accounts(self) -> list[dict[str, Any]]:
        records = json_safe(self.table("demo_credentials").to_dict(orient="records"))
        # Include one plain Employee account so the dashboard can demonstrate
        # an intentional RBAC denial without editing the immutable dataset.
        existing_ids = {str(record.get("user_id")) for record in records}
        role_rows = self.table("user_roles")
        users = self.table("users")
        for user_id, group in role_rows.groupby("user_id"):
            roles = sorted(group["role_name"].astype(str).tolist())
            if roles != ["Employee"] or str(user_id) in existing_ids:
                continue
            match = users[users["user_id"] == user_id]
            if not match.empty:
                records.append(
                    {
                        "user_id": str(user_id),
                        "email": str(match.iloc[0]["email"]),
                        "temporary_password": "Demo@123!",
                        "roles": "Employee",
                        "must_change_password": True,
                        "usage_note": "Generated demo selector entry for RBAC-denial testing.",
                    }
                )
            break
        return records

    def find_project(self, query: str) -> dict[str, Any] | None:
        projects = self.table("projects")
        query_norm = normalize_text(query)
        for _, row in projects.iterrows():
            if normalize_text(str(row["project_name"])) in query_norm:
                return json_safe(row.to_dict())
            short_name = normalize_text(str(row["project_name"]).split()[0])
            if short_name and short_name in query_norm:
                return json_safe(row.to_dict())
        names = projects["project_name"].astype(str).tolist()
        match = difflib.get_close_matches(query, names, n=1, cutoff=0.45)
        if match:
            row = projects[projects["project_name"] == match[0]].iloc[0]
            return json_safe(row.to_dict())
        return None

    def resolve_project_context(self, query: str) -> dict[str, Any]:
        """Resolve an explicitly named project without guessing unknown names."""
        projects = self.table("projects")
        query_norm = normalize_text(query)
        for _, row in projects.iterrows():
            project_id = str(row["project_id"])
            project_name = str(row["project_name"])
            aliases = {
                normalize_text(project_id),
                normalize_text(project_name),
                normalize_text(project_name).split()[0],
            }
            if any(
                alias
                and re.search(
                    rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", query_norm
                )
                for alias in aliases
            ):
                return {
                    "requested": True,
                    "found": True,
                    "project_id": project_id,
                    "project_name": project_name,
                    "requested_name": project_name,
                    "member_employee_ids": [],
                    "member_count": 0,
                }

        task_match = re.search(r"\bT\d{5}\b", query.upper())
        if task_match:
            task = self.task_record(task_match.group(0))
            if task:
                project_match = projects[
                    projects["project_id"].astype(str) == str(task["project_id"])
                ]
                if not project_match.empty:
                    row = project_match.iloc[0]
                    return {
                        "requested": True,
                        "found": True,
                        "project_id": str(row["project_id"]),
                        "project_name": str(row["project_name"]),
                        "requested_name": str(row["project_name"]),
                        "member_employee_ids": [],
                        "member_count": 0,
                        "resolved_from_task_id": task_match.group(0),
                    }

        # Only label a reference as unknown when the user supplied a concrete
        # name after "project". Generic phrases such as "project teams" remain
        # unscoped portfolio/company-wide requests.
        match = re.search(r"\bproject\s+(?:named\s+)?([a-z0-9][a-z0-9_-]*)", query_norm)
        generic_terms = {
            "and",
            "capacity",
            "employee",
            "employees",
            "health",
            "member",
            "members",
            "portfolio",
            "risk",
            "risks",
            "status",
            "team",
            "teams",
            "workload",
        }
        if match and match.group(1) not in generic_terms:
            requested_name = match.group(1).replace("_", " ").replace("-", " ").title()
            return {
                "requested": True,
                "found": False,
                "project_id": None,
                "project_name": None,
                "requested_name": requested_name,
                "member_employee_ids": [],
                "member_count": 0,
            }
        return {
            "requested": False,
            "found": None,
            "project_id": None,
            "project_name": None,
            "requested_name": None,
            "member_employee_ids": [],
            "member_count": 0,
        }

    def project_member_ids(self, project_id: str) -> list[str]:
        members = self.table("project_members")
        rows = members[members["project_id"].astype(str) == str(project_id)].copy()
        if "active" in rows.columns:
            active = rows["active"].astype(str).str.lower().isin({"true", "1", "yes"})
            rows = rows[active]
        return list(dict.fromkeys(rows["employee_id"].astype(str).tolist()))

    def project_detail(self, project_id: str) -> dict[str, Any] | None:
        projects = self.table("projects")
        match = projects[projects["project_id"] == project_id]
        if match.empty:
            return None
        project = json_safe(match.iloc[0].to_dict())
        tasks = self.tasks_with_runtime_assignments()
        task_rows = tasks[tasks["project_id"] == project_id].copy()
        members = self.table("project_members")
        member_rows = members[members["project_id"] == project_id].copy()
        risks = self.table("project_risks")
        risk_rows = risks[risks["project_id"] == project_id].copy()
        latest_workload = self.latest_workload()
        employee = self.table("employees")[["employee_id", "full_name", "job_title", "department_name"]]
        member_detail = member_rows.merge(employee, on="employee_id", how="left")
        member_detail = member_detail.merge(latest_workload, on="employee_id", how="left")
        return {
            "project": project,
            "tasks": json_safe(task_rows.to_dict(orient="records")),
            "members": json_safe(member_detail.to_dict(orient="records")),
            "risks": json_safe(risk_rows.to_dict(orient="records")),
        }

    def tasks_with_runtime_assignments(self) -> pd.DataFrame:
        tasks = self.table("tasks").copy()
        if self.runtime_store is None:
            return tasks
        overrides = self.runtime_store.task_assignment_overrides()
        if overrides:
            mapped = tasks["task_id"].astype(str).map(overrides)
            mask = mapped.notna()
            tasks.loc[mask, "assigned_to_employee_id"] = mapped[mask]
        return tasks

    def task_record(self, task_id: str, *, effective: bool = True) -> dict[str, Any] | None:
        tasks = self.tasks_with_runtime_assignments() if effective else self.table("tasks")
        match = tasks[tasks["task_id"].astype(str) == str(task_id).upper()]
        if match.empty:
            return None
        return json_safe(match.iloc[0].to_dict())

    def latest_workload(self) -> pd.DataFrame:
        frame = self.table("workload").copy()
        frame["snapshot_date"] = pd.to_datetime(frame["snapshot_date"])
        latest = frame["snapshot_date"].max()
        return frame[frame["snapshot_date"] == latest].copy()

    def employee_lookup(self, query: str) -> dict[str, Any] | None:
        employees = self.table("employees")
        query_norm = normalize_text(query)
        for _, row in employees.iterrows():
            emp_id = normalize_text(str(row["employee_id"]))
            full_name = normalize_text(str(row["full_name"]))
            if emp_id in query_norm or full_name in query_norm:
                return json_safe(row.to_dict())
        return None

    def project_names(self) -> list[str]:
        return self.table("projects")["project_name"].astype(str).tolist()

    def all_role_names(self) -> list[str]:
        return self.table("roles")["role_name"].astype(str).tolist()

    def authorized_document_rows(self, roles: list[str], permissions: list[str]) -> pd.DataFrame:
        chunks = self.table("rag_chunks").copy()
        roles_set = set(roles)
        permissions_set = set(permissions)

        def allowed(row: pd.Series) -> bool:
            row_roles = set(pipe_values(row.get("allowed_roles")))
            required_permission = str(row.get("required_permission", ""))
            role_ok = bool(roles_set.intersection(row_roles))
            permission_ok = not required_permission or required_permission in permissions_set
            return bool(row.get("active", True)) and role_ok and permission_ok

        mask = chunks.apply(allowed, axis=1)
        return chunks[mask].copy()

    def dataset_counts(self) -> dict[str, int]:
        keys = [
            "employees",
            "projects",
            "tasks",
            "sales_orders",
            "approval_requests",
            "workflow_runs",
            "agent_logs",
            "rag_chunks",
            "document_catalog",
        ]
        return {name: int(len(self.table(name))) for name in keys}

    def clear_cache(self) -> None:
        self._cache.clear()
        self.__dict__.pop("role_permission_map", None)
        self.__dict__.pop("workflow_map", None)
        self.__dict__.pop("agent_map", None)
