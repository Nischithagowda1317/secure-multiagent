from __future__ import annotations

from pathlib import Path

from app.services.llm_providers import GenerationRequest, LLMProvider, ProviderResponse
from conftest import login_headers


PROJECT_MANAGER = "majid.aleusud@nexacore.example"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
PDF_ROOT = (
    PROJECT_ROOT
    / "datasets"
    / "Secure_Multi_Agent_Enterprise_Dataset"
    / "knowledge_base"
    / "canonical_pdf"
)
SALES_POLICY_PDF = PDF_ROOT / "DOC008_Sales_Discount_and_Promotion_Policy.pdf"
ATLAS_PDF = PDF_ROOT / "DOC012_Project_Atlas_Status_Report.pdf"
SALES_POLICY_DOCX = (
    PROJECT_ROOT
    / "datasets"
    / "Secure_Multi_Agent_Enterprise_Dataset"
    / "knowledge_base"
    / "editable_docx"
    / "DOC008_Sales_Discount_and_Promotion_Policy.docx"
)


def _post_files(client, message: str, paths: list[Path]):
    headers = login_headers(client, PROJECT_MANAGER)
    streams = [path.open("rb") for path in paths]
    try:
        return client.post(
            "/api/chat",
            headers=headers,
            data={"message": message},
            files=[
                ("files", (path.name, stream, "application/pdf"))
                for path, stream in zip(paths, streams)
            ],
        )
    finally:
        for stream in streams:
            stream.close()


def _agent_ids(payload: dict) -> set[str]:
    return {agent["agent_id"] for agent in payload["agents"]}


def test_sales_policy_summary_uses_only_uploaded_pdf(client):
    response = _post_files(client, "summarize me this pdf", [SALES_POLICY_PDF])
    assert response.status_code == 200, response.text
    payload = response.json()
    routing = payload["explanation"]["routing_context"]
    attachment_validation = payload["explanation"]["validation"][
        "attachment_scope_validation"
    ]

    assert payload["workflow_id"] == "WFD001"
    assert payload["status"] == "Completed"
    assert routing["attachment_mode"] == "summary"
    assert routing["retrieval_scope"] == "attachment_only"
    assert "A003" in _agent_ids(payload)
    assert _agent_ids(payload).isdisjoint({"A004", "A005", "A006", "A007"})
    assert payload["approval"]["required"] is False
    assert attachment_validation["passed"] is True
    assert payload["explanation"]["validation"]["status"] == "PASS"
    assert payload["sources"]
    assert all(source["source_type"] == "Temporary upload" for source in payload["sources"])
    assert {source["title"] for source in payload["sources"]} == {
        SALES_POLICY_PDF.name
    }
    assert "leave requests longer" not in payload["answer"].lower()


def test_atlas_summary_uses_only_uploaded_pdf(client):
    response = _post_files(client, "summarize this pdf", [ATLAS_PDF])
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["workflow_id"] == "WFD001"
    assert payload["explanation"]["routing_context"]["retrieval_scope"] == "attachment_only"
    assert {source["title"] for source in payload["sources"]} == {ATLAS_PDF.name}
    assert all(source["source_type"] == "Temporary upload" for source in payload["sources"])
    assert not any(source["source_id"].startswith("DOC") for source in payload["sources"])


def test_word_file_summary_is_attachment_only(client):
    response = _post_files(
        client, "Give me the key points from this Word file", [SALES_POLICY_DOCX]
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["explanation"]["routing_context"]["attachment_mode"] == "summary"
    assert payload["explanation"]["routing_context"]["retrieval_scope"] == "attachment_only"
    assert {source["title"] for source in payload["sources"]} == {
        SALES_POLICY_DOCX.name
    }
    assert all(source["source_type"] == "Temporary upload" for source in payload["sources"])


def test_text_file_summary_is_attachment_only(client):
    headers = login_headers(client, PROJECT_MANAGER)
    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "Tell me what this file says"},
        files={
            "files": (
                "capacity_note.txt",
                b"Capacity note: Team Orion can accept one additional support task.",
                "text/plain",
            )
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["explanation"]["routing_context"]["retrieval_scope"] == "attachment_only"
    assert {source["title"] for source in payload["sources"]} == {
        "capacity_note.txt"
    }
    assert "Team Orion" in payload["answer"]


def test_project_report_comparison_combines_attachment_and_enterprise(client):
    response = _post_files(
        client,
        "Compare this report with current Project Atlas database status.",
        [ATLAS_PDF],
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    routing = payload["explanation"]["routing_context"]

    assert payload["workflow_id"] == "WFD002"
    assert routing["attachment_mode"] == "compare"
    assert routing["retrieval_scope"] == "attachment_plus_enterprise"
    assert {"A003", "A005"}.issubset(_agent_ids(payload))
    assert any(source["source_type"] == "Temporary upload" for source in payload["sources"])
    assert any(source["source_type"] != "Temporary upload" for source in payload["sources"])
    assert payload["explanation"]["validation"]["status"] == "PASS"


def test_unreferenced_attachment_does_not_override_enterprise_policy_query(client):
    response = _post_files(
        client, "What is the remote-work policy?", [SALES_POLICY_PDF]
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    routing = payload["explanation"]["routing_context"]

    assert routing["attachment_context_used"] is False
    assert routing["retrieval_scope"] == "enterprise_only"
    assert any(source["source_id"] == "DOC003" for source in payload["sources"])
    assert not any(source["source_type"] == "Temporary upload" for source in payload["sources"])


def test_multiple_pdf_summary_keeps_files_separate_and_attachment_only(client):
    response = _post_files(
        client, "Summarize these files.", [SALES_POLICY_PDF, ATLAS_PDF]
    )
    assert response.status_code == 200, response.text
    payload = response.json()

    assert payload["explanation"]["routing_context"]["retrieval_scope"] == "attachment_only"
    assert {source["title"] for source in payload["sources"]} == {
        SALES_POLICY_PDF.name,
        ATLAS_PDF.name,
    }
    assert f"- {SALES_POLICY_PDF.name}" in payload["answer"]
    assert f"- {ATLAS_PDF.name}" in payload["answer"]
    assert payload["explanation"]["validation"]["attachment_scope_validation"][
        "passed"
    ] is True


class UnsupportedAttachmentProvider(LLMProvider):
    name = "ollama"
    model = "llama3.1:8b"

    def __init__(self):
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(
            "Leave requests receive automatic approval at 91.62% confidence.",
            self.name,
            self.model,
            10,
        )

    async def health_check(self) -> bool:
        return True


def test_unsupported_attachment_fact_triggers_grounded_fallback(client, monkeypatch):
    services = client.app.state.services
    provider = UnsupportedAttachmentProvider()
    monkeypatch.setattr(services.llm, "provider", provider)

    response = _post_files(client, "summarize this pdf", [SALES_POLICY_PDF])
    assert response.status_code == 200, response.text
    payload = response.json()

    assert provider.requests
    assert provider.requests[0].retrieval_scope == "attachment_only"
    assert "Summarize only the supplied uploaded document content" in str(
        provider.requests[0].scope_instruction
    )
    assert services.llm.last_call is not None
    assert services.llm.last_call.fallback_used is True
    assert str(services.llm.last_call.error_status).startswith(
        "unsupported_numeric_claim:91.62%"
    )
    assert "91.62" not in payload["answer"]
    assert "leave requests" not in payload["answer"].lower()
