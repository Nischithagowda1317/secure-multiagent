from __future__ import annotations

from typing import Any

from app.agents.types import AgentResult
from app.services.repository import DataRepository


class ValidationAgent:
    agent_id = "A008"
    agent_name = "Validation Agent"

    @staticmethod
    def validate_llm_response(
        *,
        answer: str,
        error_status: str | None,
        approval_pending: bool,
        numeric_grounding_status: str = "not_applied",
        normalized_numeric_match_count: int = 0,
    ) -> dict[str, Any]:
        """Validate the released response after optional LLM generation.

        Detailed evidence grounding is enforced by the LLM service before this
        point. This validation records that result and independently protects
        the pending-approval action boundary.
        """
        grounding_guard_triggered = bool(
            error_status
            and error_status.startswith(
                (
                    "unsupported_numeric_claim",
                    "unsupported_derived_metric",
                    "unsupported_action_claim",
                )
            )
        )
        lowered = answer.lower()
        completed_action_claim = any(
            phrase in lowered
            for phrase in (
                "has been executed",
                "was executed",
                "successfully executed",
                "has been approved",
                "is approved",
            )
        )
        action_boundary_passed = not (approval_pending and completed_action_claim)
        warnings = []
        if grounding_guard_triggered:
            warnings.append(
                "LLM output failed the grounding guard; extractive fallback was used."
            )
        if not action_boundary_passed:
            warnings.append(
                "Generated text claimed completion while human approval was pending."
            )
        return {
            "applied": True,
            "passed": bool(answer.strip()) and action_boundary_passed,
            "grounding_guard_triggered": grounding_guard_triggered,
            "action_boundary_passed": action_boundary_passed,
            "fallback_used": bool(error_status),
            "error_status": error_status,
            "numeric_grounding_status": numeric_grounding_status,
            "normalized_numeric_match_count": normalized_numeric_match_count,
            "warnings": warnings,
        }

    def __init__(self, repository: DataRepository | None = None):
        self.repository = repository

    def run(
        self,
        *,
        workflow_id: str,
        results: list[AgentResult],
        router_confidence: float,
        security_decision: str,
        injection_detected: bool,
        force_approval: bool,
        query: str = "",
        project_context: dict[str, Any] | None = None,
        reassignment_plan: dict[str, Any] | None = None,
        user_permissions: list[str] | None = None,
        retrieval_scope: str = "enterprise_only",
        attached_files: list[dict[str, Any]] | None = None,
    ) -> tuple[dict[str, Any], AgentResult]:
        domain_results = [result for result in results if result.agent_id not in {"A001", "A002"}]
        source_keys = {
            (source.get("source_id"), source.get("section"), source.get("path"))
            for result in domain_results
            for source in result.sources
        }
        source_count = len(source_keys)
        result_confidences = [result.confidence for result in domain_results]
        mean_confidence = sum(result_confidences) / len(result_confidences) if result_confidences else router_confidence
        confidence = max(0.0, min(1.0, 0.25 * router_confidence + 0.75 * mean_confidence))
        needs_grounding = workflow_id in {"WFD001", "WFD010", "WFD012"}
        if source_count:
            best_domain_confidence = max(result_confidences or [router_confidence])
            grounding = min(0.99, 0.45 + 0.35 * best_domain_confidence + 0.04 * min(source_count, 4))
        else:
            grounding = 0.25
        if not needs_grounding:
            grounding = max(grounding, 0.86)
        warnings = [warning for result in results for warning in result.warnings]
        scope_validation = self._validate_project_scope(results, project_context)
        attachment_scope_validation = self._validate_attachment_scope(
            results,
            retrieval_scope=retrieval_scope,
            attached_files=attached_files or [],
        )
        reassignment_validation = self._validate_reassignment_plan(
            workflow_id=workflow_id,
            plan=reassignment_plan,
            project_context=project_context,
            user_permissions=user_permissions or [],
        )
        if scope_validation["applied"] and not scope_validation["passed"]:
            warnings.extend(scope_validation["warnings"])
            confidence = min(confidence, 0.50)
        if (
            attachment_scope_validation["applied"]
            and not attachment_scope_validation["passed"]
        ):
            warnings.extend(attachment_scope_validation["errors"])
            confidence = min(confidence, 0.40)
        if reassignment_validation["applied"] and not reassignment_validation["passed"]:
            warnings.extend(reassignment_validation["errors"])
            confidence = min(confidence, 0.45)
        if injection_detected:
            warnings.append("Prompt-injection defense was activated.")
            confidence = min(confidence, 0.82)
        if security_decision != "ALLOW":
            confidence = 1.0
            grounding = 1.0
        quality_review_recommended = confidence < 0.75 or grounding < 0.80
        if quality_review_recommended:
            warnings.append(
                "The read-only result used a safe route but has low confidence or grounding."
            )
        human_review = (
            force_approval
            or (scope_validation["applied"] and not scope_validation["passed"])
            or (
                attachment_scope_validation["applied"]
                and not attachment_scope_validation["passed"]
            )
            or (reassignment_validation["applied"] and not reassignment_validation["passed"])
        )
        status = "PASS"
        if security_decision != "ALLOW":
            status = "ACCESS_DENIED"
            human_review = False
        elif reassignment_validation["applied"] and not reassignment_validation["passed"]:
            status = "FAIL"
            human_review = False
        elif scope_validation["applied"] and not scope_validation["passed"]:
            status = "FAIL"
        elif (
            attachment_scope_validation["applied"]
            and not attachment_scope_validation["passed"]
        ):
            status = "FAIL"
            human_review = False
        elif human_review:
            status = "NEEDS_HUMAN_REVIEW"
        validation = {
            "status": status,
            "correctness_score": round(confidence, 4),
            "grounding_score": round(grounding, 4),
            "safety_score": 0.99 if not injection_detected else 0.92,
            "source_count": source_count,
            "human_review_required": human_review,
            "quality_review_recommended": quality_review_recommended,
            "project_scope_validation": scope_validation,
            "attachment_scope_validation": attachment_scope_validation,
            "reassignment_plan_validation": reassignment_validation,
            "warnings": list(dict.fromkeys(warnings)),
        }
        result = AgentResult(
            self.agent_id,
            self.agent_name,
            f"Validation status {status}; confidence {confidence:.2f}, grounding {grounding:.2f}.",
            validation,
            [
                {"source_id": "validation_rules", "title": "AI Governance and Evaluation Rules", "source_type": "Rules", "path": "core/evaluation/metrics_template.csv"}
            ],
            min(confidence, 0.99),
            validation["warnings"],
        )
        return validation, result

    @staticmethod
    def _validate_attachment_scope(
        results: list[AgentResult],
        *,
        retrieval_scope: str,
        attached_files: list[dict[str, Any]],
    ) -> dict[str, Any]:
        applied = retrieval_scope == "attachment_only"
        result = {
            "applied": applied,
            "passed": True,
            "retrieval_scope": retrieval_scope,
            "attached_filenames": [
                str(item.get("filename")) for item in attached_files
            ],
            "source_ids": [],
            "unexpected_source_ids": [],
            "unrelated_agent_ids": [],
            "missing_filenames": [],
            "errors": [],
        }
        if not applied:
            return result

        domain_results = [
            item for item in results if item.agent_id not in {"A001", "A002"}
        ]
        unrelated_agents = sorted(
            {item.agent_id for item in domain_results if item.agent_id != "A003"}
        )
        rag_sources = [
            source
            for item in domain_results
            if item.agent_id == "A003"
            for source in item.sources
        ]
        expected_filenames = set(result["attached_filenames"])
        returned_filenames = {
            str(source.get("title"))
            for source in rag_sources
            if source.get("source_type") == "Temporary upload"
        }
        unexpected_sources = [
            str(source.get("source_id", "source"))
            for source in rag_sources
            if source.get("source_type") != "Temporary upload"
            or str(source.get("title")) not in expected_filenames
        ]
        missing_filenames = sorted(expected_filenames - returned_filenames)
        errors = []
        if not rag_sources:
            errors.append("Attachment-only retrieval returned no uploaded-file sources.")
        if unexpected_sources:
            errors.append(
                "Attachment-only retrieval included non-attachment sources: "
                + ", ".join(unexpected_sources)
            )
        if unrelated_agents:
            errors.append(
                "Attachment-only retrieval invoked unrelated domain agents: "
                + ", ".join(unrelated_agents)
            )
        if missing_filenames:
            errors.append(
                "Attachment-only retrieval omitted uploaded files: "
                + ", ".join(missing_filenames)
            )
        result.update(
            {
                "passed": not errors,
                "source_ids": sorted(
                    {str(source.get("source_id", "source")) for source in rag_sources}
                ),
                "unexpected_source_ids": sorted(set(unexpected_sources)),
                "unrelated_agent_ids": unrelated_agents,
                "missing_filenames": missing_filenames,
                "errors": errors,
            }
        )
        return result

    def _validate_reassignment_plan(
        self,
        *,
        workflow_id: str,
        plan: dict[str, Any] | None,
        project_context: dict[str, Any] | None,
        user_permissions: list[str],
    ) -> dict[str, Any]:
        result = {
            "applied": workflow_id == "WFD005",
            "passed": True,
            "errors": [],
            "checks": {},
        }
        if workflow_id != "WFD005":
            return result
        if not plan:
            result["passed"] = False
            result["errors"] = ["No valid reassignment plan was prepared."]
            return result
        if self.repository is None:
            result["passed"] = False
            result["errors"] = ["Reassignment validation requires repository access."]
            return result

        errors: list[str] = []
        checks: dict[str, bool] = {}
        projects = self.repository.table("projects")
        project_id = str(plan.get("project_id", ""))
        project_exists = bool(
            (projects["project_id"].astype(str) == project_id).any()
        )
        checks["project_exists"] = project_exists
        if not project_exists:
            errors.append("The selected project does not exist.")

        task_id = str(plan.get("task_id", ""))
        task = self.repository.task_record(task_id)
        checks["task_exists"] = task is not None
        if task is None:
            errors.append("The selected task does not exist.")
        else:
            task_project_valid = str(task.get("project_id")) == project_id
            checks["task_belongs_to_project"] = task_project_valid
            if not task_project_valid:
                errors.append("The selected task does not belong to the selected project.")
            expected_source = str(plan.get("source_employee_id", ""))
            source_is_assignee = str(task.get("assigned_to_employee_id")) == expected_source
            checks["source_is_current_assignee"] = source_is_assignee
            if not source_is_assignee:
                errors.append("The source employee is not the task's current assignee.")
            open_task = str(task.get("status", "")).lower() not in {
                "completed",
                "closed",
                "cancelled",
            }
            checks["task_is_open"] = open_task
            if not open_task:
                errors.append("The selected task is completed, closed, or cancelled.")
            reassignable = bool(plan.get("task_reassignable")) and open_task
            checks["task_is_reassignable"] = reassignable
            if not reassignable:
                errors.append("The selected task is not reassignable.")

        member_ids = set(map(str, (project_context or {}).get("member_employee_ids", [])))
        source_id = str(plan.get("source_employee_id", ""))
        source_member = source_id in member_ids
        checks["source_belongs_to_project"] = source_member
        if not source_member:
            errors.append("The source employee does not belong to the selected project.")

        workload = self.repository.latest_workload()
        workload_values = {
            str(row["employee_id"]): float(row["total_workload_percent"])
            for _, row in workload.iterrows()
        }
        source_workload = workload_values.get(source_id)
        source_overloaded = (
            source_workload is not None
            and source_workload >= float(plan.get("overloaded_threshold_percent", 100.0))
        )
        checks["source_overloaded"] = source_overloaded
        if plan.get("source_overload_required") and not source_overloaded:
            errors.append("The source employee does not satisfy the overloaded threshold.")

        employees = self.repository.table("employees")
        target_id = str(plan.get("target_employee_id", ""))
        target_rows = employees[employees["employee_id"].astype(str) == target_id]
        target_exists = not target_rows.empty
        checks["target_exists"] = target_exists
        if not target_exists:
            errors.append("The target employee does not exist.")
        target_active = target_exists and str(
            target_rows.iloc[0].get("employment_status", "")
        ).lower() == "active"
        checks["target_is_active"] = target_active
        if target_exists and not target_active:
            errors.append("The target employee is not active.")
        target_workload = workload_values.get(target_id)
        target_available = (
            target_workload is not None
            and target_workload
            < float(plan.get("availability_threshold_percent", 60.0))
        )
        checks["target_is_available"] = target_available
        if not target_available:
            errors.append("The target employee is not in the available workload range.")
        different_people = bool(source_id and target_id and source_id != target_id)
        checks["target_differs_from_source"] = different_people
        if not different_people:
            errors.append("The target employee cannot be the source employee.")
        target_eligible = bool(plan.get("target_eligible")) and target_active and target_available
        checks["target_is_eligible"] = target_eligible
        if not target_eligible:
            errors.append("The target employee is not eligible to receive the task.")
        if plan.get("target_project_membership_required"):
            target_member = target_id in member_ids
            checks["target_belongs_to_project"] = target_member
            if not target_member:
                errors.append("The target employee does not belong to the selected project.")

        permission_ok = "task.reassign" in set(user_permissions)
        checks["user_has_task_reassign"] = permission_ok
        if not permission_ok:
            errors.append("The user does not have task.reassign permission.")
        hr_access_ok = "employee.read" in set(user_permissions)
        checks["authorized_hr_access"] = hr_access_ok
        if not hr_access_ok:
            errors.append("The user is not authorized to access reassignment workload details.")

        result.update(
            {
                "passed": not errors,
                "errors": list(dict.fromkeys(errors)),
                "checks": checks,
            }
        )
        return result

    @staticmethod
    def _validate_project_scope(
        results: list[AgentResult], project_context: dict[str, Any] | None
    ) -> dict[str, Any]:
        context = dict(project_context or {})
        base = {
            "applied": False,
            "passed": True,
            "project_id": context.get("project_id"),
            "checked_employee_count": 0,
            "project_id_valid": True,
            "member_context_valid": True,
            "analyzed_count_valid": True,
            "matching_count_valid": True,
            "membership_valid": True,
            "threshold_valid": True,
            "invalid_employee_ids": [],
            "invalid_workload_employee_ids": [],
            "warnings": [],
        }
        if not context.get("requested") or not context.get("found"):
            return base

        hr_result = next((result for result in results if result.agent_id == "A004"), None)
        if hr_result is None or not isinstance(hr_result.content, dict):
            return base
        if hr_result.content.get("scope") != "project":
            base.update(
                {
                    "applied": True,
                    "passed": False,
                    "membership_valid": False,
                    "warnings": ["HR result was not restricted to the requested project."],
                }
            )
            return base

        base["applied"] = True
        allowed_ids = set(map(str, context.get("member_employee_ids", [])))
        reported_project_id = str(hr_result.content.get("project_id", ""))
        project_id_valid = reported_project_id == str(context.get("project_id", ""))
        reported_member_values = hr_result.content.get("project_member_ids")
        member_context_valid = isinstance(reported_member_values, list) and set(
            map(str, reported_member_values)
        ) == allowed_ids
        try:
            analyzed_count_valid = int(
                hr_result.content.get("analyzed_employee_count")
            ) == len(allowed_ids)
        except (TypeError, ValueError):
            analyzed_count_valid = False
        employees = hr_result.content.get("employees", [])
        returned_ids = {
            str(employee.get("employee_id"))
            for employee in employees
            if isinstance(employee, dict) and employee.get("employee_id") is not None
        }
        invalid_ids = sorted(returned_ids - allowed_ids)
        try:
            matching_count_valid = int(
                hr_result.content.get("matching_employee_count")
            ) == len(employees)
        except (TypeError, ValueError):
            matching_count_valid = False
        threshold = hr_result.content.get("workload_threshold_percent")
        condition = hr_result.content.get("workload_condition")
        invalid_workloads: list[str] = []
        if threshold is not None and condition in {"overloaded", "available"}:
            for employee in employees:
                if not isinstance(employee, dict):
                    continue
                employee_id = str(employee.get("employee_id"))
                try:
                    workload = float(employee.get("total_workload_percent"))
                except (TypeError, ValueError):
                    invalid_workloads.append(employee_id)
                    continue
                valid = workload >= float(threshold) if condition == "overloaded" else workload < float(threshold)
                if not valid:
                    invalid_workloads.append(employee_id)

        warnings: list[str] = []
        if not project_id_valid:
            warnings.append("HR result project ID does not match the requested project.")
        if not member_context_valid:
            warnings.append(
                "HR result project-member metadata does not match the resolved project context."
            )
        if not analyzed_count_valid:
            warnings.append(
                "HR analyzed-employee count does not match the resolved project membership."
            )
        if not matching_count_valid:
            warnings.append("HR matching-employee count does not match the returned rows.")
        if invalid_ids:
            warnings.append(
                "Project-scoped HR result contained employees not assigned to the project: "
                + ", ".join(invalid_ids)
            )
        if invalid_workloads:
            warnings.append(
                "HR workload result contained employees that did not satisfy the requested threshold: "
                + ", ".join(sorted(set(invalid_workloads)))
            )
        base.update(
            {
                "passed": (
                    project_id_valid
                    and member_context_valid
                    and analyzed_count_valid
                    and matching_count_valid
                    and not invalid_ids
                    and not invalid_workloads
                ),
                "checked_employee_count": len(returned_ids),
                "project_id_valid": project_id_valid,
                "member_context_valid": member_context_valid,
                "analyzed_count_valid": analyzed_count_valid,
                "matching_count_valid": matching_count_valid,
                "membership_valid": not invalid_ids,
                "threshold_valid": not invalid_workloads,
                "invalid_employee_ids": invalid_ids,
                "invalid_workload_employee_ids": sorted(set(invalid_workloads)),
                "warnings": warnings,
            }
        )
        return base
