from __future__ import annotations

from pathlib import Path

from conftest import login_headers


PROJECT_MANAGER = "majid.aleusud@nexacore.example"
HR_MANAGER = "rawan.durkzili@nexacore.example"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
ATLAS_PDF = (
    PROJECT_ROOT
    / "datasets"
    / "Secure_Multi_Agent_Enterprise_Dataset"
    / "knowledge_base"
    / "canonical_pdf"
    / "DOC012_Project_Atlas_Status_Report.pdf"
)


def _post_atlas(client, headers: dict[str, str], message: str | None):
    data = {} if message is None else {"message": message}
    with ATLAS_PDF.open("rb") as stream:
        return client.post(
            "/api/chat",
            headers=headers,
            data=data,
            files={"files": (ATLAS_PDF.name, stream, "application/pdf")},
        )


def _agent_ids(payload: dict) -> set[str]:
    return {agent["agent_id"] for agent in payload["agents"]}


def test_analyze_project_attachment_uses_project_and_rag_without_leave(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = _post_atlas(client, headers, "Analyze this document.")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD002"
    assert payload["workflow_name"] == "Project Status Analysis"
    assert payload["security"]["permission"] == "project.read"
    assert {"A003", "A005"}.issubset(_agent_ids(payload))
    assert "A004" not in _agent_ids(payload)
    assert payload["approval"]["required"] is False
    assert "leave.read_own" not in payload["security"]["permission"]
    routing = payload["explanation"]["routing_context"]
    assert routing["detected_domain"] == "project"
    assert routing["detected_document_type"] == "project_status_report"
    assert routing["detected_project_id"] == "PRJ001"
    assert routing["document_classification"] == "Confidential"
    assert routing["declared_required_permission"] == "project.read"
    assert routing["backend_required_permission"] == "project.read"


def test_compare_project_attachment_uses_project_database_and_rag(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = _post_atlas(
        client, headers, "Compare this report with current Project Atlas status."
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD002"
    assert {"A003", "A005"}.issubset(_agent_ids(payload))
    project = next(
        section for section in payload["sections"] if section["title"] == "Project Agent"
    )
    assert project["content"]["project"]["project_id"] == "PRJ001"
    assert payload["explanation"]["validation"]["status"] == "PASS"
    assert payload["approval"]["required"] is False


def test_summarize_project_pdf_uses_rag_without_hr_or_approval(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = _post_atlas(client, headers, "Summarize this PDF.")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD001"
    assert payload["security"]["permission"] == "project.read"
    assert "A003" in _agent_ids(payload)
    assert "A004" not in _agent_ids(payload)
    assert payload["approval"]["required"] is False
    assert any(source["source_type"] == "Temporary upload" for source in payload["sources"])


def test_file_only_uses_safe_read_only_document_fallback(client):
    headers = login_headers(client, PROJECT_MANAGER)
    before = len(client.app.state.services.runtime_store.list_approvals())
    response = _post_atlas(client, headers, None)

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD001"
    assert payload["status"] == "Completed"
    assert payload["security"]["permission"] == "project.read"
    assert payload["approval"]["required"] is False
    assert _agent_ids(payload).isdisjoint({"A004", "A006", "A007", "A010"})
    assert len(client.app.state.services.runtime_store.list_approvals()) == before


def test_genuine_leave_balance_still_uses_leave_read_permission(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = client.post(
        "/api/chat", headers=headers, data={"message": "Show my leave balance."}
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD009"
    assert payload["security"]["permission"] == "leave.read_own"
    assert payload["approval"]["required"] is False


def test_explicit_leave_approval_still_creates_approval(client):
    headers = login_headers(client, HR_MANAGER)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "Approve leave request LR001."},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD009"
    assert payload["security"]["permission"] == "leave.read_all + leave.approve"
    assert payload["approval"]["required"] is True
    assert payload["status"] == "Awaiting Approval"


def test_low_router_confidence_uses_safe_fallback_without_approval(client, monkeypatch):
    services = client.app.state.services
    before = len(services.runtime_store.list_approvals())
    monkeypatch.setattr(services.models, "route", lambda _query: ("WFD009", 0.19))

    response = client.post(
        "/api/chat",
        headers=login_headers(client, PROJECT_MANAGER),
        data={"message": "Please help interpret this information."},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD001"
    assert payload["security"]["permission"] == "ai.query"
    assert payload["approval"]["required"] is False
    assert payload["explanation"]["routing_context"]["safe_fallback"] is True
    assert payload["explanation"]["routing_context"]["model_router_confidence"] == 0.19
    assert len(services.runtime_store.list_approvals()) == before


def test_unrelated_text_takes_precedence_over_project_attachment(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = _post_atlas(client, headers, "What is the remote-work policy?")

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["workflow_id"] == "WFD001"
    assert payload["security"]["permission"] == "ai.query"
    assert payload["explanation"]["routing_context"]["attachment_context_used"] is False
    assert any(source["source_id"] == "DOC003" for source in payload["sources"])
    assert not any(source["source_type"] == "Temporary upload" for source in payload["sources"])
    assert payload["approval"]["required"] is False
