from __future__ import annotations

import pytest

from conftest import login_headers


EMPLOYEE = "rayid.zazana@nexacore.example"
PROJECT_MANAGER = "majid.aleusud@nexacore.example"
NOVA_QUERY = (
    "Reassign one overloaded Project Nova member's task to Alaa Alrifaei "
    "after checking workload and project risk."
)


@pytest.fixture(autouse=True)
def clean_reassignment_runtime(client):
    store = client.app.state.services.runtime_store
    with store._lock, store.connect() as connection:
        connection.execute("DELETE FROM task_assignment_overrides")
        connection.execute("DELETE FROM runtime_approvals")
        connection.execute(
            "DELETE FROM audit_events WHERE event_type LIKE 'task_reassignment_%'"
        )
    yield


def _chat(client, message: str, email: str = PROJECT_MANAGER) -> dict:
    response = client.post(
        "/api/chat",
        headers=login_headers(client, email),
        data={"message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _runtime_approval(client, approval_id: str) -> dict:
    record = client.app.state.services.runtime_store.get_approval(approval_id)
    assert record is not None
    return record


def _create_nova_approval(client) -> tuple[dict, dict]:
    payload = _chat(client, NOVA_QUERY)
    approval_id = payload["approval"]["approval_id"]
    return payload, _runtime_approval(client, approval_id)


def _approve(client, approval_id: str, decision: str = "Approved"):
    return client.post(
        f"/api/approvals/{approval_id}/decision",
        headers=login_headers(client, PROJECT_MANAGER),
        json={"decision": decision, "comment": f"Test decision: {decision}"},
    )


def test_generic_nova_request_selects_real_task_without_preapproval_mutation(client):
    services = client.app.state.services
    payload, approval = _create_nova_approval(client)
    plan = approval["payload_json"]["reassignment_plan"]
    raw_task = services.repository.task_record(plan["task_id"], effective=False)
    effective_task = services.repository.task_record(plan["task_id"])

    assert payload["status"] == "Awaiting Approval"
    assert approval["business_object_id"] == plan["task_id"]
    assert approval["business_object_id"] != "UNSPECIFIED_TASK"
    assert plan["project_id"] == "PRJ002"
    assert raw_task["project_id"] == "PRJ002"
    assert plan["source_workload_percent"] >= 100
    assert plan["target_employee_id"] == "E0140"
    assert plan["target_workload_percent"] < 60
    assert effective_task["assigned_to_employee_id"] == plan["source_employee_id"]
    assert "Reassignment plan prepared and awaiting approval." in payload["answer"]


def test_explicit_task_id_is_never_replaced_by_auto_selection(client):
    payload = _chat(client, "Reassign Task T00025 to Alaa Yuzbik.")
    approval = _runtime_approval(client, payload["approval"]["approval_id"])
    plan = approval["payload_json"]["reassignment_plan"]

    assert payload["status"] == "Awaiting Approval"
    assert approval["business_object_id"] == "T00025"
    assert plan["task_id"] == "T00025"
    assert plan["explicit_task_requested"] is True


def test_approve_executes_task_and_writes_complete_audit(client):
    services = client.app.state.services
    _, approval = _create_nova_approval(client)
    plan = approval["payload_json"]["reassignment_plan"]

    response = _approve(client, approval["approval_id"])
    assert response.status_code == 200, response.text
    updated = response.json()
    effective_task = services.repository.task_record(plan["task_id"])
    audit = next(
        event
        for event in services.runtime_store.recent_audit(100)
        if event["event_type"] == "task_reassignment_executed"
        and event["details_json"]["approval_id"] == approval["approval_id"]
    )

    assert updated["status"] == "Approved"
    assert updated["execution_status"] == "Executed"
    assert effective_task["assigned_to_employee_id"] == plan["target_employee_id"]
    for key in (
        "task_id",
        "project_id",
        "old_assignee",
        "new_assignee",
        "requested_by",
        "approved_by",
        "timestamp",
        "reason",
        "approval_id",
    ):
        assert audit["details_json"].get(key) is not None


def test_reject_keeps_task_unchanged_and_writes_audit(client):
    services = client.app.state.services
    _, approval = _create_nova_approval(client)
    plan = approval["payload_json"]["reassignment_plan"]

    response = _approve(client, approval["approval_id"], "Rejected")
    assert response.status_code == 200, response.text
    effective_task = services.repository.task_record(plan["task_id"])
    audits = services.runtime_store.recent_audit(100)

    assert response.json()["status"] == "Rejected"
    assert effective_task["assigned_to_employee_id"] == plan["source_employee_id"]
    assert any(
        event["event_type"] == "task_reassignment_rejected"
        and event["details_json"]["approval_id"] == approval["approval_id"]
        for event in audits
    )


def test_double_approve_is_blocked_and_not_executed_twice(client):
    services = client.app.state.services
    _, approval = _create_nova_approval(client)

    first = _approve(client, approval["approval_id"])
    second = _approve(client, approval["approval_id"])
    matching_audits = [
        event
        for event in services.runtime_store.recent_audit(100)
        if event["event_type"] == "task_reassignment_executed"
        and event["details_json"]["approval_id"] == approval["approval_id"]
    ]

    assert first.status_code == 200
    assert second.status_code == 409
    assert "only Pending approvals" in second.json()["detail"]
    assert len(matching_audits) == 1


def test_overloaded_target_prevents_approval(client):
    payload = _chat(
        client,
        "Reassign one overloaded Project Nova member's task to Sara Tabanaj.",
    )

    assert payload["status"] == "Validation Failed"
    assert payload["approval"]["required"] is False
    assert "not in the available workload range" in payload["answer"]


def test_no_eligible_open_task_prevents_approval(client):
    payload = _chat(
        client,
        "Reassign one overloaded Project Mercury member's task to Aishah Alquatliu.",
    )

    assert payload["status"] == "Validation Failed"
    assert payload["approval"]["required"] is False
    assert "No eligible open task" in payload["answer"]


def test_unauthorized_user_is_denied_before_plan_or_approval(client):
    payload = _chat(client, NOVA_QUERY, EMPLOYEE)

    assert payload["status"] == "Access Denied"
    assert "task.reassign" in payload["security"]["permission"]
    assert payload["approval"]["required"] is False


def test_stale_approval_is_blocked_without_overwrite(client):
    services = client.app.state.services
    _, first = _create_nova_approval(client)
    _, stale = _create_nova_approval(client)
    first_plan = first["payload_json"]["reassignment_plan"]
    stale_plan = stale["payload_json"]["reassignment_plan"]
    assert first_plan["task_id"] == stale_plan["task_id"]

    assert _approve(client, first["approval_id"]).status_code == 200
    response = _approve(client, stale["approval_id"])
    stale_record = _runtime_approval(client, stale["approval_id"])
    effective_task = services.repository.task_record(stale_plan["task_id"])

    assert response.status_code == 409
    assert "Stale reassignment plan" in response.json()["detail"]
    assert stale_record["status"] == "Execution Blocked"
    assert effective_task["assigned_to_employee_id"] == first_plan["target_employee_id"]


def test_generic_selection_works_for_another_project(client):
    payload = _chat(
        client,
        "Reassign one overloaded Project Helios member's task to Muhamad Alzaybq.",
    )
    approval = _runtime_approval(client, payload["approval"]["approval_id"])
    plan = approval["payload_json"]["reassignment_plan"]

    assert payload["status"] == "Awaiting Approval"
    assert plan["project_id"] == "PRJ003"
    assert plan["target_employee_id"] == "E0057"
    assert plan["task_id"].startswith("T")
    assert approval["business_object_id"] == plan["task_id"]
