#!/usr/bin/env python3
"""Validate the NexaCore Secure Multi-Agent Enterprise Assistant dataset.

Uses only the Python standard library. Run from any working directory:
    python scripts/validate_dataset.py
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Iterable

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "core"

PKS = {
    "departments": ("department_id",), "roles": ("role_id",), "permissions": ("permission_id",),
    "users": ("user_id",), "employees": ("employee_id",), "user_roles": ("user_id", "role_id"),
    "role_permissions": ("role_id", "permission_id"), "employee_skills": ("employee_skill_id",),
    "attendance_summary": ("attendance_id",), "employee_workload_snapshots": ("snapshot_id",),
    "leave_requests": ("leave_request_id",), "projects": ("project_id",),
    "project_members": ("project_member_id",), "tasks": ("task_id",),
    "task_dependencies": ("dependency_id",), "project_risks": ("risk_id",),
    "products": ("product_id",), "customers": ("customer_id",), "suppliers": ("supplier_id",),
    "sales_orders": ("order_id",), "purchase_requests": ("purchase_request_id",),
    "expense_claims": ("expense_claim_id",), "agent_registry": ("agent_id",),
    "tool_registry": ("tool_id",), "agent_tool_permissions": ("agent_tool_permission_id",),
    "workflow_definitions": ("workflow_definition_id",), "workflow_runs": ("workflow_run_id",),
    "agent_execution_logs": ("agent_execution_log_id",), "approval_requests": ("approval_request_id",),
    "approval_actions": ("approval_action_id",), "access_control_decisions": ("access_decision_id",),
    "audit_logs": ("audit_log_id",), "document_catalog": ("document_id",),
    "rag_chunks": ("chunk_id",), "rag_evaluation_questions": ("question_id",),
    "evaluation_programs": ("program_id",), "evaluation_runs": ("eval_run_id",),
    "evaluation_items": ("eval_item_id",), "judge_results": ("judge_result_id",),
    "reviewer_decisions": ("review_id",), "daily_evaluation_metrics": ("metric_id",),
}

FKS = [
    ("employees", "department_id", "departments", "department_id"),
    ("users", "employee_id", "employees", "employee_id"),
    ("user_roles", "user_id", "users", "user_id"), ("user_roles", "role_id", "roles", "role_id"),
    ("role_permissions", "role_id", "roles", "role_id"),
    ("role_permissions", "permission_id", "permissions", "permission_id"),
    ("employee_skills", "employee_id", "employees", "employee_id"),
    ("attendance_summary", "employee_id", "employees", "employee_id"),
    ("employee_workload_snapshots", "employee_id", "employees", "employee_id"),
    ("leave_requests", "employee_id", "employees", "employee_id"),
    ("leave_requests", "approver_employee_id", "employees", "employee_id"),
    ("projects", "business_owner_department_id", "departments", "department_id"),
    ("projects", "project_manager_employee_id", "employees", "employee_id"),
    ("project_members", "project_id", "projects", "project_id"),
    ("project_members", "employee_id", "employees", "employee_id"),
    ("tasks", "project_id", "projects", "project_id"),
    ("tasks", "assigned_to_employee_id", "employees", "employee_id"),
    ("tasks", "created_by_employee_id", "employees", "employee_id"),
    ("task_dependencies", "predecessor_task_id", "tasks", "task_id"),
    ("task_dependencies", "successor_task_id", "tasks", "task_id"),
    ("project_risks", "project_id", "projects", "project_id"),
    ("customers", "account_manager_employee_id", "employees", "employee_id"),
    ("sales_orders", "customer_id", "customers", "customer_id"),
    ("sales_orders", "product_id", "products", "product_id"),
    ("sales_orders", "account_manager_employee_id", "employees", "employee_id"),
    ("purchase_requests", "requester_employee_id", "employees", "employee_id"),
    ("purchase_requests", "department_id", "departments", "department_id"),
    ("purchase_requests", "supplier_id", "suppliers", "supplier_id"),
    ("expense_claims", "employee_id", "employees", "employee_id"),
    ("agent_tool_permissions", "agent_id", "agent_registry", "agent_id"),
    ("agent_tool_permissions", "tool_id", "tool_registry", "tool_id"),
    ("workflow_runs", "workflow_definition_id", "workflow_definitions", "workflow_definition_id"),
    ("workflow_runs", "user_id", "users", "user_id"),
    ("agent_execution_logs", "workflow_run_id", "workflow_runs", "workflow_run_id"),
    ("agent_execution_logs", "agent_id", "agent_registry", "agent_id"),
    ("agent_execution_logs", "tool_id", "tool_registry", "tool_id"),
    ("approval_requests", "requested_by_user_id", "users", "user_id"),
    ("approval_actions", "approval_request_id", "approval_requests", "approval_request_id"),
    ("approval_actions", "approver_user_id", "users", "user_id"),
    ("access_control_decisions", "user_id", "users", "user_id"),
    ("rag_chunks", "document_id", "document_catalog", "document_id"),
    ("evaluation_runs", "program_id", "evaluation_programs", "program_id"),
    ("evaluation_items", "eval_run_id", "evaluation_runs", "eval_run_id"),
    ("evaluation_items", "program_id", "evaluation_programs", "program_id"),
    ("judge_results", "eval_item_id", "evaluation_items", "eval_item_id"),
    ("reviewer_decisions", "eval_item_id", "evaluation_items", "eval_item_id"),
]


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def table_paths() -> dict[str, Path]:
    paths = {}
    for path in CORE.rglob("*.csv"):
        if path.stem in paths:
            raise ValueError(f"Duplicate table stem: {path.stem}")
        paths[path.stem] = path
    return paths


def parse_iso_date(value: str) -> date:
    return date.fromisoformat(value[:10])


def validate() -> dict:
    errors: list[str] = []
    warnings: list[str] = []
    paths = table_paths()
    tables = {name: read_csv(path) for name, path in paths.items()}

    if len(paths) < 50:
        errors.append(f"Expected at least 50 core CSV tables; found {len(paths)}.")

    # Basic structure and primary-key uniqueness.
    for name, rows in tables.items():
        if not rows:
            errors.append(f"{name}: contains no data rows.")
        if name in PKS:
            cols = PKS[name]
            seen = set()
            for row_no, row in enumerate(rows, start=2):
                key = tuple(row.get(c, "") for c in cols)
                if any(v == "" for v in key):
                    errors.append(f"{name} row {row_no}: blank primary-key component {cols}.")
                    continue
                if key in seen:
                    errors.append(f"{name} row {row_no}: duplicate primary key {key}.")
                seen.add(key)

    # Foreign-key checks.
    parent_values: dict[tuple[str, str], set[str]] = {}
    for _, _, parent, parent_col in FKS:
        parent_values[(parent, parent_col)] = {r[parent_col] for r in tables[parent] if r.get(parent_col, "")}
    for child, child_col, parent, parent_col in FKS:
        allowed = parent_values[(parent, parent_col)]
        bad = sorted({r.get(child_col, "") for r in tables[child] if r.get(child_col, "") and r.get(child_col, "") not in allowed})
        if bad:
            errors.append(f"{child}.{child_col}: {len(bad)} missing references to {parent}.{parent_col}; examples={bad[:5]}")

    # Knowledge-base files and catalogue.
    catalog = tables["document_catalog"]
    for row in catalog:
        for col in ("canonical_pdf_path", "editable_docx_path"):
            path = ROOT / row[col]
            if not path.exists() or path.stat().st_size == 0:
                errors.append(f"Document {row['document_id']}: missing or empty {col}: {path}")
    if len(catalog) != 14:
        warnings.append(f"Expected 14 knowledge documents; found {len(catalog)}.")

    # Deterministic demonstration facts.
    snapshot = date(2026, 8, 28)
    tasks = tables["tasks"]
    def project_counts(project_id: str) -> tuple[int, int]:
        relevant = [r for r in tasks if r["project_id"] == project_id]
        overdue = sum(r["status"] != "Completed" and parse_iso_date(r["due_date"]) < snapshot for r in relevant)
        blocked = sum(r["status"] == "Blocked" for r in relevant)
        return overdue, blocked
    if project_counts("PRJ001") != (6, 2):
        errors.append(f"Atlas fact mismatch: expected overdue/blocked=(6,2), got {project_counts('PRJ001')}.")
    if project_counts("PRJ002") != (1, 0):
        errors.append(f"Nova fact mismatch: expected overdue/blocked=(1,0), got {project_counts('PRJ002')}.")

    current_workload = {
        r["employee_id"]: float(r["total_workload_percent"])
        for r in tables["employee_workload_snapshots"] if r["snapshot_date"] == "2026-08-28"
    }
    if current_workload.get("E0013") != 125.0 or current_workload.get("E0017") != 112.0:
        errors.append("Atlas workload facts do not match E0013=125 and E0017=112.")

    # Required security and evaluation coverage.
    if len(tables["security_test_cases"]) != len(tables["roles"]) * len(tables["permissions"]):
        errors.append("Security test matrix is not the complete roles x permissions matrix.")
    if not tables["prompt_injection_tests"]:
        errors.append("Prompt-injection tests are missing.")

    result = {
        "status": "PASS" if not errors else "FAIL",
        "root": str(ROOT),
        "core_csv_tables": len(paths),
        "core_rows": sum(len(rows) for rows in tables.values()),
        "knowledge_documents": len(catalog),
        "errors": errors,
        "warnings": warnings,
    }
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", dest="json_path", help="Optional path for a JSON validation report")
    args = parser.parse_args()
    result = validate()
    print(json.dumps(result, indent=2))
    if args.json_path:
        Path(args.json_path).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
