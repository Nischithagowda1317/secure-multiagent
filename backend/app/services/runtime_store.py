from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.utils.json_tools import dumps


class RuntimeStore:
    """SQLite store for mutable demo state.

    The curated CSVs remain immutable. All user actions are recorded here so the
    original dataset can be reset simply by deleting runtime/assistant_runtime.db.
    """

    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS runtime_approvals (
                    approval_id TEXT PRIMARY KEY,
                    base_approval_id TEXT,
                    request_type TEXT NOT NULL,
                    business_object_type TEXT NOT NULL,
                    business_object_id TEXT NOT NULL,
                    requested_action TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    risk_tier TEXT NOT NULL,
                    required_roles TEXT NOT NULL,
                    status TEXT NOT NULL,
                    requested_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    resolved_at TEXT,
                    resolved_by TEXT,
                    decision_comment TEXT
                );
                CREATE TABLE IF NOT EXISTS uploaded_documents (
                    document_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    filename TEXT NOT NULL,
                    classification TEXT NOT NULL,
                    allowed_roles TEXT NOT NULL,
                    required_permission TEXT NOT NULL,
                    stored_path TEXT NOT NULL,
                    extracted_text_path TEXT NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    uploaded_by TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS audit_events (
                    audit_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    resource_type TEXT,
                    resource_id TEXT,
                    decision TEXT,
                    details_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS chat_history (
                    chat_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    workflow_run_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    response_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS task_assignment_overrides (
                    task_id TEXT PRIMARY KEY,
                    original_assignee_employee_id TEXT NOT NULL,
                    current_assignee_employee_id TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def add_audit(
        self,
        user_id: str,
        event_type: str,
        resource_type: str | None,
        resource_id: str | None,
        decision: str | None,
        details: dict[str, Any],
    ) -> str:
        audit_id = f"RTAUD-{uuid.uuid4().hex[:12].upper()}"
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO audit_events
                (audit_id, user_id, event_type, resource_type, resource_id, decision, details_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    user_id,
                    event_type,
                    resource_type,
                    resource_id,
                    decision,
                    dumps(details),
                    self.now(),
                ),
            )
        return audit_id

    def recent_audit(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM audit_events ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [self._row(row) for row in rows]

    def save_chat(
        self, user_id: str, workflow_run_id: str, query: str, response: dict[str, Any]
    ) -> str:
        chat_id = f"CHAT-{uuid.uuid4().hex[:12].upper()}"
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO chat_history
                (chat_id, user_id, workflow_run_id, query, response_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (chat_id, user_id, workflow_run_id, query, dumps(response), self.now()),
            )
        return chat_id

    def create_approval(
        self,
        *,
        request_type: str,
        business_object_type: str,
        business_object_id: str,
        requested_action: str,
        payload: dict[str, Any],
        risk_tier: str,
        required_roles: list[str],
        requested_by: str,
        base_approval_id: str | None = None,
    ) -> dict[str, Any]:
        approval_id = f"RTAPR-{uuid.uuid4().hex[:12].upper()}"
        created_at = self.now()
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO runtime_approvals
                (approval_id, base_approval_id, request_type, business_object_type,
                 business_object_id, requested_action, payload_json, risk_tier,
                 required_roles, status, requested_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Pending', ?, ?)
                """,
                (
                    approval_id,
                    base_approval_id,
                    request_type,
                    business_object_type,
                    business_object_id,
                    requested_action,
                    dumps(payload),
                    risk_tier,
                    "|".join(required_roles),
                    requested_by,
                    created_at,
                ),
            )
        return self.get_approval(approval_id) or {}

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runtime_approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
        return self._row(row) if row else None

    def list_approvals(self, status: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
        query = "SELECT * FROM runtime_approvals"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        query += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [self._row(row) for row in rows]

    def decide_approval(
        self, approval_id: str, decision: str, resolved_by: str, comment: str
    ) -> dict[str, Any] | None:
        normalized = decision.strip().capitalize()
        if normalized not in {"Approved", "Rejected", "Cancelled"}:
            raise ValueError("Decision must be Approved, Rejected, or Cancelled")
        with self._lock, self.connect() as connection:
            cursor = connection.execute(
                """
                UPDATE runtime_approvals
                SET status = ?, resolved_at = ?, resolved_by = ?, decision_comment = ?
                WHERE approval_id = ? AND status = 'Pending'
                """,
                (normalized, self.now(), resolved_by, comment, approval_id),
            )
            if cursor.rowcount != 1:
                return None
        return self.get_approval(approval_id)

    def task_assignment_overrides(self) -> dict[str, str]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT task_id, current_assignee_employee_id FROM task_assignment_overrides"
            ).fetchall()
        return {
            str(row["task_id"]): str(row["current_assignee_employee_id"])
            for row in rows
        }

    def execute_task_reassignment(
        self,
        approval_id: str,
        *,
        resolved_by: str,
        comment: str,
        base_assignee_employee_id: str,
    ) -> tuple[dict[str, Any] | None, str, str]:
        """Atomically execute a pending reassignment approval.

        Returns ``(record, outcome, reason)`` where outcome is one of
        ``executed``, ``stale``, ``not_pending``, or ``invalid_plan``.
        """
        outcome = "invalid_plan"
        reason = "Approval does not contain a valid reassignment plan."
        now = self.now()
        with self._lock, self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runtime_approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            if row is None:
                return None, "not_found", "Approval not found."
            raw = dict(row)
            if str(raw["status"]) != "Pending":
                record = self._row(row)
                return (
                    record,
                    "not_pending",
                    f"Approval is {raw['status']}; only Pending approvals can be executed.",
                )
            try:
                payload = json.loads(str(raw["payload_json"]))
            except json.JSONDecodeError:
                payload = {}
            plan = payload.get("reassignment_plan") if isinstance(payload, dict) else None
            if not isinstance(plan, dict) or not plan.get("task_id"):
                return self._row(row), outcome, reason

            task_id = str(plan["task_id"])
            expected_source = str(plan.get("source_employee_id", ""))
            override = connection.execute(
                "SELECT current_assignee_employee_id FROM task_assignment_overrides WHERE task_id = ?",
                (task_id,),
            ).fetchone()
            current_assignee = (
                str(override["current_assignee_employee_id"])
                if override
                else str(base_assignee_employee_id)
            )
            if current_assignee != expected_source:
                reason = (
                    f"Stale reassignment plan: task {task_id} is assigned to "
                    f"{current_assignee}, not expected source {expected_source}."
                )
                connection.execute(
                    """
                    UPDATE runtime_approvals
                    SET status = 'Execution Blocked', resolved_at = ?, resolved_by = ?,
                        decision_comment = ?
                    WHERE approval_id = ? AND status = 'Pending'
                    """,
                    (now, resolved_by, reason, approval_id),
                )
                self._insert_audit(
                    connection,
                    user_id=resolved_by,
                    event_type="task_reassignment_blocked",
                    resource_type="task",
                    resource_id=task_id,
                    decision="Execution Blocked",
                    details={
                        **plan,
                        "approval_id": approval_id,
                        "requested_by": raw["requested_by"],
                        "approved_by": resolved_by,
                        "timestamp": now,
                        "stale_current_assignee": current_assignee,
                        "reason": reason,
                    },
                )
                outcome = "stale"
            else:
                target_employee_id = str(plan["target_employee_id"])
                connection.execute(
                    """
                    INSERT INTO task_assignment_overrides
                    (task_id, original_assignee_employee_id, current_assignee_employee_id,
                     approval_id, updated_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(task_id) DO UPDATE SET
                        current_assignee_employee_id = excluded.current_assignee_employee_id,
                        approval_id = excluded.approval_id,
                        updated_at = excluded.updated_at
                    """,
                    (
                        task_id,
                        base_assignee_employee_id,
                        target_employee_id,
                        approval_id,
                        now,
                    ),
                )
                connection.execute(
                    """
                    UPDATE runtime_approvals
                    SET status = 'Approved', resolved_at = ?, resolved_by = ?,
                        decision_comment = ?
                    WHERE approval_id = ? AND status = 'Pending'
                    """,
                    (now, resolved_by, comment, approval_id),
                )
                self._insert_audit(
                    connection,
                    user_id=resolved_by,
                    event_type="task_reassignment_executed",
                    resource_type="task",
                    resource_id=task_id,
                    decision="Approved",
                    details={
                        **plan,
                        "approval_id": approval_id,
                        "old_assignee": expected_source,
                        "new_assignee": target_employee_id,
                        "requested_by": raw["requested_by"],
                        "approved_by": resolved_by,
                        "timestamp": now,
                        "decision_comment": comment,
                    },
                )
                outcome = "executed"
                reason = "Task reassignment executed after approval."
        record = self.get_approval(approval_id)
        if record is not None and outcome == "executed":
            record["execution_status"] = "Executed"
        return record, outcome, reason

    def block_approval_execution(
        self,
        approval_id: str,
        *,
        resolved_by: str,
        reason: str,
        plan: dict[str, Any],
    ) -> dict[str, Any] | None:
        now = self.now()
        with self._lock, self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM runtime_approvals WHERE approval_id = ?", (approval_id,)
            ).fetchone()
            if row is None or str(row["status"]) != "Pending":
                return self._row(row) if row else None
            connection.execute(
                """
                UPDATE runtime_approvals
                SET status = 'Execution Blocked', resolved_at = ?, resolved_by = ?,
                    decision_comment = ?
                WHERE approval_id = ? AND status = 'Pending'
                """,
                (now, resolved_by, reason, approval_id),
            )
            self._insert_audit(
                connection,
                user_id=resolved_by,
                event_type="task_reassignment_blocked",
                resource_type="task",
                resource_id=str(plan.get("task_id", "")),
                decision="Execution Blocked",
                details={
                    **plan,
                    "approval_id": approval_id,
                    "requested_by": row["requested_by"],
                    "approved_by": resolved_by,
                    "timestamp": now,
                    "reason": reason,
                },
            )
        return self.get_approval(approval_id)

    def _insert_audit(
        self,
        connection: sqlite3.Connection,
        *,
        user_id: str,
        event_type: str,
        resource_type: str | None,
        resource_id: str | None,
        decision: str | None,
        details: dict[str, Any],
    ) -> str:
        audit_id = f"RTAUD-{uuid.uuid4().hex[:12].upper()}"
        connection.execute(
            """
            INSERT INTO audit_events
            (audit_id, user_id, event_type, resource_type, resource_id, decision, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                audit_id,
                user_id,
                event_type,
                resource_type,
                resource_id,
                decision,
                dumps(details),
                self.now(),
            ),
        )
        return audit_id

    def add_uploaded_document(
        self,
        *,
        title: str,
        filename: str,
        classification: str,
        allowed_roles: list[str],
        required_permission: str,
        stored_path: str,
        extracted_text_path: str,
        chunk_count: int,
        uploaded_by: str,
    ) -> dict[str, Any]:
        document_id = f"UPDOC-{uuid.uuid4().hex[:10].upper()}"
        with self._lock, self.connect() as connection:
            connection.execute(
                """
                INSERT INTO uploaded_documents
                (document_id, title, filename, classification, allowed_roles,
                 required_permission, stored_path, extracted_text_path, chunk_count,
                 uploaded_by, created_at, active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    document_id,
                    title,
                    filename,
                    classification,
                    "|".join(allowed_roles),
                    required_permission,
                    stored_path,
                    extracted_text_path,
                    chunk_count,
                    uploaded_by,
                    self.now(),
                ),
            )
        return self.get_uploaded_document(document_id) or {}

    def get_uploaded_document(self, document_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM uploaded_documents WHERE document_id = ?", (document_id,)
            ).fetchone()
        return self._row(row) if row else None

    def list_uploaded_documents(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                "SELECT * FROM uploaded_documents WHERE active = 1 ORDER BY created_at DESC"
            ).fetchall()
        return [self._row(row) for row in rows]

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        value = dict(row)
        for key in ("payload_json", "details_json", "response_json"):
            if key in value and value[key]:
                try:
                    value[key] = json.loads(value[key])
                except json.JSONDecodeError:
                    pass
        if "required_roles" in value and isinstance(value["required_roles"], str):
            value["required_roles"] = [
                part for part in value["required_roles"].split("|") if part
            ]
        if "allowed_roles" in value and isinstance(value["allowed_roles"], str):
            value["allowed_roles"] = [
                part for part in value["allowed_roles"].split("|") if part
            ]
        if (
            value.get("request_type") == "Task Reassignment"
            and value.get("status") == "Approved"
        ):
            value["execution_status"] = "Executed"
        return value
