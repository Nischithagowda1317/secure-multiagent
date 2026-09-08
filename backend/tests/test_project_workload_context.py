from __future__ import annotations

from app.agents.types import AgentResult
from app.agents.validation_agent import ValidationAgent
from conftest import login_headers


EMPLOYEE = "rayid.zazana@nexacore.example"
PROJECT_MANAGER = "majid.aleusud@nexacore.example"


def _chat(client, email: str, message: str) -> dict:
    response = client.post(
        "/api/chat",
        headers=login_headers(client, email),
        data={"message": message},
    )
    assert response.status_code == 200, response.text
    return response.json()


def _section(payload: dict, title: str) -> dict:
    return next(section for section in payload["sections"] if section["title"] == title)


def test_atlas_workload_is_limited_to_project_members(client):
    payload = _chat(
        client,
        PROJECT_MANAGER,
        "Check Project Atlas status and identify overloaded team members.",
    )

    assert payload["workflow_id"] == "WFD003"
    assert payload["status"] == "Completed"
    project = _section(payload, "Project Agent")["content"]
    hr = _section(payload, "HR Agent")["content"]
    returned_ids = {employee["employee_id"] for employee in hr["employees"]}

    assert project["project"]["project_id"] == "PRJ001"
    assert project["task_metrics"]["overdue_unfinished"] == 6
    assert project["task_metrics"]["blocked"] == 2
    assert hr["scope"] == "project"
    assert hr["project_id"] == "PRJ001"
    assert hr["analyzed_employee_count"] == 10
    assert hr["workload_condition"] == "overloaded"
    assert hr["workload_threshold_percent"] == 100.0
    assert hr["matching_employee_count"] == 3
    assert returned_ids == {"E0013", "E0079", "E0017"}
    assert returned_ids <= set(project["project_context"]["member_employee_ids"])
    assert payload["explanation"]["data_scope"] == hr["scope_explanation"]
    assert "HR Agent analyzed 10 members assigned to Atlas ERP Integration" in hr["scope_explanation"]
    assert payload["explanation"]["validation"]["project_scope_validation"]["passed"] is True
    assert payload["explanation"]["validation"]["status"] == "PASS"
    for employee_id in returned_ids:
        assert employee_id in payload["answer"]


def test_company_wide_overload_query_remains_company_wide(client):
    payload = _chat(client, PROJECT_MANAGER, "Which employees are overloaded?")

    assert payload["workflow_id"] == "WFD003"
    hr = _section(payload, "HR Agent")["content"]
    assert hr["scope"] == "company"
    assert hr["project_id"] is None
    assert hr["analyzed_employee_count"] == 200
    assert hr["matching_employee_count"] > 3
    assert payload["explanation"]["validation"]["project_scope_validation"]["applied"] is False


def test_nova_workload_is_limited_to_nova_members(client):
    payload = _chat(
        client,
        PROJECT_MANAGER,
        "Which Project Nova team members are overloaded?",
    )

    project = _section(payload, "Project Agent")["content"]
    hr = _section(payload, "HR Agent")["content"]
    returned_ids = {employee["employee_id"] for employee in hr["employees"]}
    member_ids = set(project["project_context"]["member_employee_ids"])

    assert project["project"]["project_id"] == "PRJ002"
    assert payload["status"] == "Completed"
    assert hr["project_id"] == "PRJ002"
    assert hr["analyzed_employee_count"] == 14
    assert returned_ids == {"E0200", "E0054", "E0091", "E0128"}
    assert returned_ids <= member_ids
    assert payload["explanation"]["validation"]["status"] == "PASS"
    assert payload["explanation"]["validation"]["project_scope_validation"]["passed"] is True


def test_project_with_no_overloaded_members_returns_clear_message(client):
    hr_agent = client.app.state.services.orchestrator.hr_agent
    result = hr_agent.run(
        "Which Low Capacity Test Project team members are overloaded?",
        {},
        {
            "requested": True,
            "found": True,
            "project_id": "TEST-LOW",
            "project_name": "Low Capacity Test Project",
            "requested_name": "Low Capacity Test Project",
            "member_employee_ids": ["E0140"],
            "member_count": 1,
        },
    )

    assert result.summary == "No overloaded team members were found for this project."
    assert result.content["analyzed_employee_count"] == 1
    assert result.content["employees"] == []
    validation, _ = client.app.state.services.orchestrator.validation_agent.run(
        workflow_id="WFD003",
        results=[result],
        router_confidence=0.9,
        security_decision="ALLOW",
        injection_detected=False,
        force_approval=False,
        project_context={
            "requested": True,
            "found": True,
            "project_id": "TEST-LOW",
            "project_name": "Low Capacity Test Project",
            "member_employee_ids": ["E0140"],
            "member_count": 1,
        },
    )
    assert validation["status"] == "PASS"
    assert validation["project_scope_validation"]["passed"] is True


def test_unknown_project_returns_not_found_without_company_hr_fallback(client):
    payload = _chat(
        client,
        PROJECT_MANAGER,
        "Which Project Atlantis team members are overloaded?",
    )

    assert payload["status"] == "Completed"
    assert payload["answer"] == "- Project 'Atlantis' was not found."
    assert _section(payload, "Project Agent")["content"]["project_found"] is False
    assert not any(section["title"] == "HR Agent" for section in payload["sections"])


def test_unauthorized_project_hr_request_is_denied_by_rbac(client):
    payload = _chat(
        client,
        EMPLOYEE,
        "Check Project Atlas status and identify overloaded team members.",
    )

    assert payload["status"] == "Access Denied"
    assert payload["security"]["decision"] == "DENY"
    assert "employee.read" in payload["security"]["permission"]
    assert not any(
        section["title"] in {"Project Agent", "HR Agent"}
        for section in payload["sections"]
    )


def test_validation_rejects_employee_outside_project_scope():
    context = {
        "requested": True,
        "found": True,
        "project_id": "PRJ001",
        "project_name": "Atlas ERP Integration",
        "member_employee_ids": ["E0013"],
        "member_count": 1,
    }
    bad_hr_result = AgentResult(
        agent_id="A004",
        agent_name="HR Agent",
        summary="Invalid test result",
        content={
            "scope": "project",
            "workload_condition": "overloaded",
            "workload_threshold_percent": 100.0,
            "employees": [
                {
                    "employee_id": "E0200",
                    "full_name": "Unrelated Employee",
                    "total_workload_percent": 114.4,
                },
                {
                    "employee_id": "E0013",
                    "full_name": "Assigned But Below Threshold",
                    "total_workload_percent": 99.0,
                }
            ],
        },
        sources=[{"source_id": "workload"}],
    )

    validation, _ = ValidationAgent().run(
        workflow_id="WFD003",
        results=[bad_hr_result],
        router_confidence=0.9,
        security_decision="ALLOW",
        injection_detected=False,
        force_approval=False,
        project_context=context,
    )

    scope = validation["project_scope_validation"]
    assert validation["status"] == "FAIL"
    assert scope["membership_valid"] is False
    assert scope["invalid_employee_ids"] == ["E0200"]
    assert scope["threshold_valid"] is False
    assert scope["invalid_workload_employee_ids"] == ["E0013"]
    assert validation["human_review_required"] is True
