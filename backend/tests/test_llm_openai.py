from __future__ import annotations

import asyncio
import json
from typing import Any

import httpx
import pytest

from app.services.llm_providers import (
    GenerationRequest,
    LLMProvider,
    OpenAIProvider,
    ProviderResponse,
)
from app.services.llm_service import LLMService
from app.settings import Settings
from conftest import login_headers


PROJECT_MANAGER = "majid.aleusud@nexacore.example"
EMPLOYEE = "rayid.zazana@nexacore.example"


def _response(text):
    return {"status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": text}]}]}


def _settings() -> Settings:
    return Settings(
        llm_provider="openai",
        llm_fallback_provider="extractive",
        openai_api_key="test-api-key",
        openai_model="gpt-4.1-mini",
        openai_timeout_seconds=0.1,
    )


def test_openai_provider_success_uses_authorized_payload_only():
    captured: dict[str, Any] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/responses"
        assert request.headers["Authorization"] == "Bearer test-api-key"
        captured.update(json.loads(request.content))
        assert "test-api-key" not in request.content.decode()
        return httpx.Response(
            200,
            json=_response("Based on the provided JSON, the enterprise response is: Atlas progress is 58%."),
            request=request,
        )

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://openai.test"
        ) as client:
            provider = OpenAIProvider(
                api_key="test-api-key",
                model="gpt-4.1-mini",
                timeout_seconds=1,
                client=client,
            )
            service = LLMService(_settings(), provider=provider)
            answer = await service.synthesize(
                "What is Atlas progress?",
                [
                    {
                        "document_id": "DOC-ATLAS",
                        "chunk_text": "Authorized progress is 58%.",
                        "score": 0.9162,
                        "allowed_roles": "Project Manager",
                        "unrelated_confidential_row": "must-never-be-sent",
                    }
                ],
                [],
            )
            return answer, service.metrics()

    answer, metrics = asyncio.run(scenario())
    prompt = captured["input"]
    assert answer == "Atlas progress is 58%."
    assert captured["store"] is False
    assert "Return only the final enterprise answer" in captured["instructions"]
    assert "Do not calculate, derive, infer" in captured["instructions"]
    assert "from this JSON" not in prompt
    assert "Authorized progress is 58%." in prompt
    assert "allowed_roles" not in prompt
    assert "must-never-be-sent" not in prompt
    assert '"score"' not in prompt
    assert metrics["last_call"]["fallback_used"] is False
    assert metrics["last_call"]["prompt_token_approx"] > 0


@pytest.mark.parametrize("status", [401, 429, 500])
def test_api_errors_fall_back_without_exposing_response_details(status, caplog):
    async def handler(request):
        return httpx.Response(status, json={"error": {"message": "private-error-detail"}}, request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openai.test") as client:
            provider = OpenAIProvider(api_key="test-api-key", model="gpt-4.1-mini", timeout_seconds=1, client=client)
            service = LLMService(_settings(), provider=provider)
            return await service.synthesize("Question", [], [], fallback_text="Fallback answer")

    assert asyncio.run(scenario()) == "Fallback answer"
    assert "private-error-detail" not in caplog.text
    assert "test-api-key" not in caplog.text


def test_missing_key_uses_fallback_without_network():
    async def handler(request):
        pytest.fail("Missing API key must not send a request")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openai.test") as client:
            provider = OpenAIProvider(api_key="", model="gpt-4.1-mini", timeout_seconds=1, client=client)
            service = LLMService(_settings(), provider=provider)
            assert await provider.health_check() is False
            return await service.synthesize("Question", [], [], fallback_text="Fallback answer")

    assert asyncio.run(scenario()) == "Fallback answer"


@pytest.mark.parametrize("body", [
    {"status": "incomplete", "output": []},
    {"status": "completed", "output": []},
    {"status": "completed", "output": [{"type": "message", "role": "assistant", "content": [{"type": "refusal", "refusal": "Refused"}]}]},
])
def test_incomplete_empty_or_refusal_responses_use_fallback(body):
    async def handler(request):
        return httpx.Response(200, json=body, request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openai.test") as client:
            provider = OpenAIProvider(api_key="test-api-key", model="gpt-4.1-mini", timeout_seconds=1, client=client)
            return await LLMService(_settings(), provider=provider).synthesize("Question", [], [], fallback_text="Fallback answer")

    assert asyncio.run(scenario()) == "Fallback answer"


def test_response_output_skips_reasoning_and_joins_text_messages():
    body = _response("First paragraph")
    body["output"].insert(0, {"type": "reasoning", "summary": []})
    body["output"].extend(_response("Second paragraph")["output"])

    async def handler(request):
        return httpx.Response(200, json=body, request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openai.test") as client:
            provider = OpenAIProvider(api_key="test-api-key", model="gpt-4.1-mini", timeout_seconds=1, client=client)
            return await provider.generate(GenerationRequest(query="Question"))

    assert asyncio.run(scenario()).text == "First paragraph\nSecond paragraph"


def test_health_checks_model_access_and_omits_key():
    async def handler(request):
        assert request.method == "GET"
        assert request.url.path == "/v1/models/gpt-4.1-mini"
        assert request.headers["Authorization"] == "Bearer test-api-key"
        return httpx.Response(200, json={"id": "gpt-4.1-mini"}, request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="https://openai.test") as client:
            provider = OpenAIProvider(api_key="test-api-key", model="gpt-4.1-mini", timeout_seconds=1, client=client)
            return await LLMService(_settings(), provider=provider).health_check()

    assert asyncio.run(scenario()) == {"llm_provider": "openai", "llm_available": True, "llm_model": "gpt-4.1-mini", "fallback_provider": "extractive"}
    assert "test-api-key" not in repr(_settings())


def test_service_builds_openai_provider_from_settings():
    service = LLMService(_settings())
    assert isinstance(service.provider, OpenAIProvider)
    assert service.generative_enabled


def test_openai_timeout_uses_extractive_fallback():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timed out", request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://openai.test"
        ) as client:
            provider = OpenAIProvider(
                api_key="test-api-key",
                model="gpt-4.1-mini",
                timeout_seconds=0.01,
                client=client,
            )
            service = LLMService(_settings(), provider=provider)
            answer = await service.synthesize(
                "question",
                [],
                [],
                fallback_text="Here is the response:\nDeterministic fallback",
            )
            return answer, service.last_call

    answer, metrics = asyncio.run(scenario())
    assert answer == "Deterministic fallback"
    assert metrics is not None and metrics.fallback_used is True
    assert "ReadTimeout" in str(metrics.error_status)


def test_openai_unavailable_does_not_break_generation():
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://openai.test"
        ) as client:
            provider = OpenAIProvider(
                api_key="test-api-key",
                model="gpt-4.1-mini",
                timeout_seconds=0.1,
                client=client,
            )
            service = LLMService(_settings(), provider=provider)
            return await service.synthesize(
                "question", [], [], fallback_text="Application remains available"
            )

    assert asyncio.run(scenario()) == "Application remains available"


def test_hallucinated_numeric_claim_is_replaced_by_fallback():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_response("Atlas progress is 99%."),
            request=request,
        )

    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://openai.test"
        ) as client:
            provider = OpenAIProvider(
                api_key="test-api-key",
                model="gpt-4.1-mini",
                timeout_seconds=1,
                client=client,
            )
            service = LLMService(_settings(), provider=provider)
            answer = await service.synthesize(
                "What is Atlas progress?",
                [],
                [{"title": "Project", "content": {"progress": 58}}],
                fallback_text="Atlas progress is 58%.",
            )
            return answer, service.last_call

    answer, metrics = asyncio.run(scenario())
    assert answer == "Atlas progress is 58%."
    assert metrics is not None and metrics.fallback_used is True
    assert str(metrics.error_status).startswith("unsupported_numeric_claim")


class CapturingOpenAIProvider(LLMProvider):
    name = "openai"
    model = "gpt-4.1-mini"

    def __init__(self, text: str):
        self.text = text
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(self.text, self.name, self.model, 10)

    async def health_check(self) -> bool:
        return True


def test_authorized_atlas_context_only_is_sent_to_openai(client, monkeypatch):
    llm = client.app.state.services.llm
    provider = CapturingOpenAIProvider(
        "Atlas is at 58% versus 78%, with 6 overdue tasks and 2 blocked tasks. "
        "Overloaded members are E0013, E0079, and E0017."
    )
    monkeypatch.setattr(llm, "provider", provider)

    response = client.post(
        "/api/chat",
        headers=login_headers(client, PROJECT_MANAGER),
        data={"message": "Check Project Atlas status and identify overloaded team members."},
    )

    assert response.status_code == 200, response.text
    assert provider.requests
    sections = provider.requests[-1].structured_sections
    hr = next(section for section in sections if section["title"] == "HR Agent")
    returned_ids = {row["employee_id"] for row in hr["content"]["employees"]}
    assert returned_ids == {"E0013", "E0079", "E0017"}
    assert hr["content"]["scope"] == "project"


def test_unauthorized_salary_is_denied_before_openai_call(client, monkeypatch):
    llm = client.app.state.services.llm
    provider = CapturingOpenAIProvider("This must not be called.")
    monkeypatch.setattr(llm, "provider", provider)

    response = client.post(
        "/api/chat",
        headers=login_headers(client, EMPLOYEE),
        data={"message": "Show the annual salary of employee E0013."},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "Access Denied"
    assert provider.requests == []


def test_rag_sends_authorized_chunks_and_backend_keeps_sources(client, monkeypatch):
    llm = client.app.state.services.llm
    provider = CapturingOpenAIProvider("Employees may work remotely two days per week.")
    monkeypatch.setattr(llm, "provider", provider)
    headers = login_headers(client, EMPLOYEE)
    profile = client.get("/api/auth/me", headers=headers).json()

    response = client.post(
        "/api/chat",
        headers=headers,
        data={"message": "What is the remote-work policy?"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    rag_request = next(request for request in provider.requests if request.evidence)
    assert rag_request.evidence
    assert any(item.get("document_id") == "DOC003" for item in rag_request.evidence)
    for item in rag_request.evidence:
        required = str(item.get("required_permission") or "")
        allowed_roles = {
            role for role in str(item.get("allowed_roles") or "").split("|") if role
        }
        assert not required or required in profile["permissions"]
        assert not allowed_roles or allowed_roles.intersection(profile["roles"])
    assert any(source["source_id"] == "DOC003" for source in payload["sources"])


def test_sensitive_reassignment_llm_cannot_execute(client, monkeypatch):
    services = client.app.state.services
    llm = services.llm
    provider = CapturingOpenAIProvider(
        "A reassignment plan is prepared and is awaiting human approval."
    )
    monkeypatch.setattr(llm, "provider", provider)

    response = client.post(
        "/api/chat",
        headers=login_headers(client, PROJECT_MANAGER),
        data={"message": "Reassign Task T00025 to Alaa Yuzbik."},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    approval = services.runtime_store.get_approval(payload["approval"]["approval_id"])
    plan = approval["payload_json"]["reassignment_plan"]
    task = services.repository.task_record(plan["task_id"])
    assert payload["status"] == "Awaiting Approval"
    assert approval["status"] == "Pending"
    assert task["assigned_to_employee_id"] == plan["source_employee_id"]


def test_llm_cannot_override_approval_rejection(client, monkeypatch):
    services = client.app.state.services
    provider = CapturingOpenAIProvider(
        "The reassignment has been approved and successfully executed."
    )
    monkeypatch.setattr(services.llm, "provider", provider)

    response = client.post(
        "/api/chat",
        headers=login_headers(client, PROJECT_MANAGER),
        data={"message": "Reassign Task T00025 to Alaa Yuzbik."},
    )
    payload = response.json()
    approval_id = payload["approval"]["approval_id"]
    approval = services.runtime_store.get_approval(approval_id)
    plan = approval["payload_json"]["reassignment_plan"]
    assert "successfully executed" not in payload["answer"].lower()
    assert payload["explanation"]["validation"]["llm_response_validation"][
        "grounding_guard_triggered"
    ] is True

    rejection = client.post(
        f"/api/approvals/{approval_id}/decision",
        headers=login_headers(client, PROJECT_MANAGER),
        json={"decision": "Rejected", "comment": "Rejected in LLM boundary test"},
    )
    task = services.repository.task_record(plan["task_id"])
    assert rejection.status_code == 200, rejection.text
    assert rejection.json()["status"] == "Rejected"
    assert task["assigned_to_employee_id"] == plan["source_employee_id"]
