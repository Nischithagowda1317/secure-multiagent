from __future__ import annotations

from conftest import login_headers


ADMIN = "abd.alruhmin.alnasar@nexacore.example"
EMPLOYEE = "rayid.zazana@nexacore.example"
PROJECT_MANAGER = "majid.aleusud@nexacore.example"


def test_health_and_demo_accounts(client):
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    accounts = client.get("/api/auth/demo-accounts")
    assert accounts.status_code == 200
    assert any(item["roles"] == ["Employee"] for item in accounts.json())


def test_login_and_overview(client):
    headers = login_headers(client, ADMIN)
    me = client.get("/api/auth/me", headers=headers)
    assert me.status_code == 200
    assert "Admin" in me.json()["roles"]
    overview = client.get("/api/dashboard/overview", headers=headers)
    assert overview.status_code == 200
    assert overview.json()["dataset_counts"]["employees"] == 200
    assert overview.json()["dataset_counts"]["projects"] == 18


def test_secure_rag_remote_work_answer(client):
    headers = login_headers(client, EMPLOYEE)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "What is the remote-work policy?"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD001"
    assert payload["status"] == "Completed"
    assert "two days per week" in payload["answer"].lower()
    assert any(source["source_id"] == "DOC003" for source in payload["sources"])
    assert payload["grounding_score"] >= 0.80


def test_employee_salary_access_is_denied(client):
    headers = login_headers(client, EMPLOYEE)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "Show the annual salary of employee E0013."},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["workflow_id"] == "WFD004"
    assert payload["status"] == "Access Denied"
    assert payload["security"]["decision"] == "DENY"
    assert "employee.salary.read" in payload["security"]["permission"]


def test_project_atlas_deterministic_facts(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={
            "message": "Analyze Project Atlas status and identify overloaded team members."
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD003"
    project_section = next(
        section for section in payload["sections"] if section["title"] == "Project Agent"
    )
    metrics = project_section["content"]["task_metrics"]
    assert metrics["overdue_unfinished"] == 6
    assert metrics["blocked"] == 2
    assert project_section["content"]["project"]["current_progress_percent"] == 58
    workloads = [
        row["total_workload_percent"]
        for row in project_section["content"]["overloaded_members"]
    ]
    assert 125 in workloads
    assert 112 in workloads


def test_task_reassignment_creates_hitl_approval(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={
            "message": "Reassign Task T00025 to Alaa Yuzbik after checking workload and project risk."
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD005"
    assert payload["status"] == "Awaiting Approval"
    assert payload["approval"]["required"] is True
    assert payload["approval"]["approval_id"].startswith("RTAPR-")


def test_model_registry_has_pretrained_artifacts(client):
    headers = login_headers(client, ADMIN)
    response = client.get("/api/models", headers=headers)
    assert response.status_code == 200
    models = {item["model_name"]: item for item in response.json()}
    for name in (
        "router",
        "workload",
        "task_risk",
        "sales_approval",
        "hitl",
        "agent_performance",
        "rag",
    ):
        assert models[name]["available"] is True
