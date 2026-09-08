from __future__ import annotations

import pytest

from conftest import login_headers


PROJECT_MANAGER = "majid.aleusud@nexacore.example"


@pytest.mark.parametrize(
    "query",
    [
        "Reassign Task T00025 to Alaa Alrifaei.",
        "Move T00025 from Shilan to Alaa.",
        "Assign one overloaded Nova member's task to Alaa.",
        "Please reassign this task.",
        "Change the assignee of T00025.",
        "Reallocate T00025 to another employee.",
    ],
)
def test_documented_action_phrases_have_explicit_mutation_intent(client, query):
    plan, _ = client.app.state.services.orchestrator.coordinator.plan(query)

    assert plan["workflow_id"] == "WFD005"
    assert plan["reassignment_action_intent"] is True
    assert plan["sensitive_action_requested"] is True


@pytest.mark.parametrize(
    "query",
    [
        "Which employees are available for reassignment?",
        "Who can take reassigned work?",
        "Which Nova members have capacity for reassignment?",
        "Who would be suitable for a task reassignment?",
        "Show employees available to receive work.",
        "Which overloaded team members need reassignment?",
        "Who has capacity below 60%?",
    ],
)
def test_documented_informational_phrases_never_select_mutation(client, query):
    plan, _ = client.app.state.services.orchestrator.coordinator.plan(query)

    assert plan["workflow_id"] != "WFD005"
    assert plan["reassignment_action_intent"] is False


@pytest.fixture(autouse=True)
def clean_reassignment_intent_runtime(client):
    store = client.app.state.services.runtime_store
    with store._lock, store.connect() as connection:
        connection.execute("DELETE FROM task_assignment_overrides")
        connection.execute("DELETE FROM runtime_approvals")
    yield


def _chat(client, message: str) -> dict:
    response = client.post(
        "/api/chat",
        headers=login_headers(client, PROJECT_MANAGER),
        data={"message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _section(payload: dict, title: str) -> dict:
    return next(section for section in payload["sections"] if section["title"] == title)


def _assert_read_only_capacity(payload: dict) -> dict:
    assert payload["workflow_id"] == "WFD003"
    assert payload["status"] == "Completed"
    assert payload["security"]["permission"] == "project.read + employee.read"
    assert "task.reassign" not in payload["security"]["permission"]
    assert payload["approval"]["required"] is False
    assert payload["explanation"]["validation"]["status"] == "PASS"
    assert payload["explanation"]["routing_context"][
        "reassignment_action_intent"
    ] is False
    assert payload["explanation"]["routing_context"][
        "reassignment_read_only_intent"
    ] is True
    assert all(
        "reassignment_plan" not in section.get("content", {})
        for section in payload["sections"]
        if isinstance(section.get("content"), dict)
    )
    return _section(payload, "HR Agent")["content"]


def test_available_for_reassignment_is_read_only_capacity_analysis(client):
    before = len(client.app.state.services.runtime_store.list_approvals())
    payload = _chat(
        client, "Which Project Nova team members are available for reassignment?"
    )
    hr = _assert_read_only_capacity(payload)
    employee_ids = {row["employee_id"] for row in hr["employees"]}

    assert hr["project_id"] == "PRJ002"
    assert hr["workload_condition"] == "available"
    assert hr["workload_threshold_percent"] == 60.0
    assert employee_ids == {"E0140"}
    assert len(client.app.state.services.runtime_store.list_approvals()) == before


def test_capacity_to_receive_reassigned_work_is_read_only(client):
    payload = _chat(
        client, "Who in Project Nova has capacity to receive reassigned work?"
    )
    hr = _assert_read_only_capacity(payload)

    assert {row["employee_id"] for row in hr["employees"]} == {"E0140"}


def test_overloaded_members_needing_reassignment_is_read_only(client):
    payload = _chat(
        client, "Which overloaded Project Atlas members should have work reassigned?"
    )
    hr = _assert_read_only_capacity(payload)

    assert hr["workload_condition"] == "overloaded"
    assert {row["employee_id"] for row in hr["employees"]} == {
        "E0013",
        "E0079",
        "E0017",
    }


def test_explicit_task_reassignment_remains_wfd005(client):
    payload = _chat(client, "Reassign Task T00025 to Alaa Alrifaei.")

    assert payload["workflow_id"] == "WFD005"
    assert "task.reassign" in payload["security"]["permission"]
    assert payload["status"] == "Awaiting Approval"
    assert payload["approval"]["required"] is True
    assert payload["explanation"]["routing_context"][
        "reassignment_action_intent"
    ] is True


def test_generic_overloaded_task_reassignment_remains_wfd005(client):
    payload = _chat(
        client,
        "Reassign one overloaded Project Nova member's task to Alaa Alrifaei.",
    )

    assert payload["workflow_id"] == "WFD005"
    assert payload["status"] == "Awaiting Approval"
    assert payload["approval"]["required"] is True
    approval = client.app.state.services.runtime_store.get_approval(
        payload["approval"]["approval_id"]
    )
    assert approval["payload_json"]["reassignment_plan"]["project_id"] == "PRJ002"


def test_specific_employee_capacity_question_is_read_only(client):
    payload = _chat(client, "Can Alaa Alrifaei take a reassigned Nova task?")
    hr = _assert_read_only_capacity(payload)

    assert hr["target_employee"]["employee_id"] == "E0140"
    assert hr["target_employee"]["eligible"] is True
    assert payload["approval"]["required"] is False


def test_bare_reassignment_uses_safe_read_only_fallback(client):
    payload = _chat(client, "reassignment")

    assert payload["workflow_id"] != "WFD005"
    assert payload["workflow_id"] == "WFD001"
    assert payload["security"]["permission"] == "ai.query"
    assert payload["approval"]["required"] is False
    routing = payload["explanation"]["routing_context"]
    assert routing["safe_fallback"] is True
    assert routing["reassignment_action_intent"] is False
