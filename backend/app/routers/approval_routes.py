from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from app.schemas import ApprovalDecisionRequest
from app.security.auth import current_user
from app.utils.json_tools import json_safe
from app.utils.text import pipe_values


router = APIRouter(prefix="/api/approvals", tags=["Human-in-the-Loop"])


@router.get("")
async def list_approvals(request: Request, user=Depends(current_user)):
    services = request.app.state.services
    auth = services.rbac.authorize(
        user=user,
        permission="approval.review",
        resource_type="approval",
        input_text="list approvals",
    )
    if auth.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=auth.decision.reason)
    runtime = services.runtime_store.list_approvals()
    source = services.repository.table("approval_requests")
    pending = source[source["status"] == "Pending"].head(50)
    source_records = []
    for _, row in pending.iterrows():
        record = json_safe(row.to_dict())
        record["approval_id"] = record.pop("approval_request_id")
        record["required_roles"] = pipe_values(record.get("required_approver_roles"))
        record["origin"] = "dataset"
        source_records.append(record)
    for record in runtime:
        record["origin"] = "runtime"
    return {"runtime": runtime, "dataset_pending": source_records}


@router.post("/{approval_id}/decision")
async def decide(
    approval_id: str,
    payload: ApprovalDecisionRequest,
    request: Request,
    user=Depends(current_user),
):
    services = request.app.state.services
    auth = services.rbac.authorize(
        user=user,
        permission="approval.review",
        resource_type="approval",
        resource_id=approval_id,
        input_text=f"{payload.decision} approval {approval_id}",
    )
    if auth.decision.decision != "ALLOW":
        raise HTTPException(status_code=403, detail=auth.decision.reason)

    record = services.runtime_store.get_approval(approval_id)
    if record is None and approval_id.startswith("APR"):
        source = services.repository.table("approval_requests")
        match = source[source["approval_request_id"] == approval_id]
        if match.empty:
            raise HTTPException(status_code=404, detail="Approval not found")
        source_record = json_safe(match.iloc[0].to_dict())
        record = services.runtime_store.create_approval(
            request_type=source_record["request_type"],
            business_object_type=source_record["business_object_type"],
            business_object_id=source_record["business_object_id"],
            requested_action=source_record["requested_action"],
            payload={"source_record": source_record},
            risk_tier=source_record["risk_tier"],
            required_roles=pipe_values(source_record["required_approver_roles"]),
            requested_by=source_record["requested_by_user_id"],
            base_approval_id=approval_id,
        )
        approval_id = record["approval_id"]

    if record is None:
        raise HTTPException(status_code=404, detail="Approval not found")
    if record.get("status") != "Pending":
        raise HTTPException(
            status_code=409,
            detail=(
                f"Approval is {record.get('status')}; only Pending approvals can be decided."
            ),
        )
    required_roles = set(record.get("required_roles", []))
    user_roles = set(user.get("roles", []))
    if required_roles and not required_roles.intersection(user_roles) and "Admin" not in user_roles:
        raise HTTPException(
            status_code=403,
            detail=f"One of these roles is required: {', '.join(sorted(required_roles))}",
        )
    normalized_decision = payload.decision.strip().capitalize()
    approval_payload = record.get("payload_json", {})
    reassignment_plan = (
        approval_payload.get("reassignment_plan")
        if isinstance(approval_payload, dict)
        else None
    )
    if record.get("request_type") == "Task Reassignment" and normalized_decision == "Approved":
        if not isinstance(reassignment_plan, dict):
            raise HTTPException(
                status_code=409,
                detail="Approval does not contain a valid reassignment plan.",
            )
        task_id = str(reassignment_plan.get("task_id", ""))
        base_task = services.repository.task_record(task_id, effective=False)
        if base_task is None:
            reason = f"Task {task_id} no longer exists."
            services.runtime_store.block_approval_execution(
                approval_id,
                resolved_by=str(user["user_id"]),
                reason=reason,
                plan=reassignment_plan,
            )
            raise HTTPException(status_code=409, detail=reason)
        execution_errors = []
        if str(base_task.get("project_id")) != str(reassignment_plan.get("project_id")):
            execution_errors.append("The task no longer belongs to the expected project.")
        if str(base_task.get("status", "")).lower() in {"completed", "closed", "cancelled"}:
            execution_errors.append("The task is no longer open and reassignable.")
        target_id = str(reassignment_plan.get("target_employee_id", ""))
        employees = services.repository.table("employees")
        target_rows = employees[employees["employee_id"].astype(str) == target_id]
        if target_rows.empty:
            execution_errors.append("The target employee no longer exists.")
        elif str(target_rows.iloc[0].get("employment_status", "")).lower() != "active":
            execution_errors.append("The target employee is no longer active.")
        current_workload = services.repository.latest_workload()
        target_workload_rows = current_workload[
            current_workload["employee_id"].astype(str) == target_id
        ]
        availability_threshold = float(
            reassignment_plan.get("availability_threshold_percent", 60.0)
        )
        if (
            target_workload_rows.empty
            or float(target_workload_rows.iloc[0]["total_workload_percent"])
            >= availability_threshold
        ):
            execution_errors.append(
                "The target employee is no longer in the available workload range."
            )
        if execution_errors:
            reason = " ".join(execution_errors)
            services.runtime_store.block_approval_execution(
                approval_id,
                resolved_by=str(user["user_id"]),
                reason=reason,
                plan=reassignment_plan,
            )
            raise HTTPException(status_code=409, detail=reason)
        updated, outcome, reason = services.runtime_store.execute_task_reassignment(
            approval_id,
            resolved_by=str(user["user_id"]),
            comment=payload.comment,
            base_assignee_employee_id=str(base_task["assigned_to_employee_id"]),
        )
        if outcome != "executed":
            raise HTTPException(status_code=409, detail=reason)
        return updated

    updated = services.runtime_store.decide_approval(
        approval_id,
        normalized_decision,
        str(user["user_id"]),
        payload.comment,
    )
    if not updated:
        raise HTTPException(status_code=409, detail="Approval could not be updated")
    event_type = (
        "task_reassignment_rejected"
        if record.get("request_type") == "Task Reassignment"
        and normalized_decision == "Rejected"
        else "approval_decision"
    )
    audit_details = {
        "comment": payload.comment,
        "business_object_id": updated["business_object_id"],
        "approval_id": approval_id,
        "requested_by": record.get("requested_by"),
        "approved_by": str(user["user_id"]),
    }
    if isinstance(reassignment_plan, dict):
        audit_details.update(reassignment_plan)
        audit_details.update(
            {
                "old_assignee": reassignment_plan.get("source_employee_id"),
                "new_assignee": reassignment_plan.get("target_employee_id"),
                "timestamp": services.runtime_store.now(),
            }
        )
    services.runtime_store.add_audit(
        user_id=str(user["user_id"]),
        event_type=event_type,
        resource_type="approval",
        resource_id=approval_id,
        decision=updated["status"],
        details=audit_details,
    )
    return updated
