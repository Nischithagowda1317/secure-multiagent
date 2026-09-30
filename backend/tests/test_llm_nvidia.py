import asyncio
import json

import httpx
import pytest

from app.services.llm_providers import GenerationRequest, NvidiaProvider
from app.services.llm_service import LLMService
from app.settings import Settings
from conftest import login_headers


def completion(text="Remote work requires approval.", finish_reason="stop"):
    return {"choices": [{"finish_reason": finish_reason, "message": {
        "role": "assistant", "content": text,
    }}]}


def test_nvidia_provider_selection_and_secret_redaction():
    config = Settings(llm_provider="nvidia", nvidia_api_key="nvapi-test-secret")
    service = LLMService(config)
    assert isinstance(service.provider, NvidiaProvider)
    assert service.generative_enabled
    assert service.provider.model == "meta/llama-3.3-70b-instruct"
    assert "nvapi-test-secret" not in repr(config)


def test_nvidia_uses_hosted_chat_endpoint_and_authorized_context(monkeypatch):
    async def handler(request):
        assert str(request.url) == "https://integrate.api.nvidia.com/v1/chat/completions"
        assert request.headers["Authorization"] == "Bearer nvapi-test-secret"
        payload = json.loads(request.content)
        assert payload["model"] == "meta/llama-3.3-70b-instruct"
        assert payload["stream"] is False
        assert payload["messages"][0]["role"] == "system"
        prompt = payload["messages"][1]["content"]
        assert "Remote work requires approval." in prompt
        assert "private-row" not in prompt
        assert "nvapi-test-secret" not in request.content.decode()
        return httpx.Response(200, json=completion())

    # Exercise the real client construction, including the production host.
    original_client = httpx.AsyncClient
    monkeypatch.setattr(httpx, "AsyncClient", lambda **kwargs: original_client(
        transport=httpx.MockTransport(handler), **kwargs,
    ))
    service = LLMService(Settings(llm_provider="nvidia", nvidia_api_key="nvapi-test-secret"))
    answer = asyncio.run(service.synthesize("Remote work policy?", [{
        "chunk_text": "Remote work requires approval.", "unrelated_row": "private-row",
    }], []))
    assert answer == "Remote work requires approval."
    assert service.last_call.provider == "nvidia"
    assert service.last_call.fallback_used is False


@pytest.mark.parametrize("status,body", [
    (401, {"error": {"message": "nvapi-test-secret"}}),
    (429, {"error": {"message": "nvapi-test-secret"}}),
    (500, {}),
    (200, completion("Partial answer", "length")),
    (200, completion(None)),
    (200, {"choices": None}),
])
def test_nvidia_failures_use_fallback_without_exposing_key(status, body, caplog):
    async def scenario():
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(status, json=body)),
            base_url=NvidiaProvider.base_url,
        ) as client:
            provider = NvidiaProvider(api_key="nvapi-test-secret", model="test", timeout_seconds=1, client=client)
            service = LLMService(Settings(llm_provider="nvidia"), provider=provider)
            answer = await service.synthesize("Question", [], [], fallback_text="Fallback answer")
            assert service.last_call.fallback_used is True
            return answer

    assert asyncio.run(scenario()) == "Fallback answer"
    assert "nvapi-test-secret" not in caplog.text


def test_nvidia_missing_key_never_calls_network():
    def handler(request):
        pytest.fail("Missing credentials must not send a request")

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            provider = NvidiaProvider(api_key="", model="test", timeout_seconds=1, client=client)
            assert await provider.health_check() is False
            with pytest.raises(ValueError, match="NVIDIA_API_KEY"):
                await provider.generate(GenerationRequest(query="Question"))

    asyncio.run(scenario())


def test_nvidia_timeout_uses_fallback():
    def handler(request):
        raise httpx.ReadTimeout("Timed out", request=request)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=NvidiaProvider.base_url) as client:
            provider = NvidiaProvider(api_key="test", model="test", timeout_seconds=1, client=client)
            service = LLMService(Settings(llm_provider="nvidia"), provider=provider)
            assert await service.synthesize("Question", [], [], fallback_text="Fallback answer") == "Fallback answer"
            assert service.last_call.fallback_used is True

    asyncio.run(scenario())


@pytest.mark.parametrize("models,expected", [
    ([{"id": "test"}], True), ([{"id": "other"}], False), (None, False),
])
def test_nvidia_health_checks_selected_model(models, expected):
    def handler(request):
        assert request.url.path == "/v1/models"
        return httpx.Response(200, json={"data": models})

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url=NvidiaProvider.base_url) as client:
            provider = NvidiaProvider(api_key="test", model="test", timeout_seconds=1, client=client)
            return await provider.health_check()

    assert asyncio.run(scenario()) is expected


@pytest.mark.parametrize("status", [200, 401])
def test_nvidia_chat_workflow_keeps_answer_and_nullable_sources(client, monkeypatch, status):
    calls = []

    async def request(method, path, **kwargs):
        calls.append(kwargs["payload"])
        return httpx.Response(
            status,
            json=completion("Atlas progress is 58%."),
            request=httpx.Request(method, NvidiaProvider.base_url + path),
        )

    provider = NvidiaProvider(api_key="test", model="test", timeout_seconds=1)
    monkeypatch.setattr(provider, "_request", request)
    llm = client.app.state.services.llm
    monkeypatch.setattr(llm, "provider", provider)
    response = client.post("/api/chat", headers=login_headers(client, "majid.aleusud@nexacore.example"), data={
        "message": "Analyze Project Atlas status and identify overloaded team members.",
    })
    assert response.status_code == 200, response.text
    payload = response.json()
    assert calls
    assert payload["answer"]
    assert any(source["score"] is None for source in payload["sources"])
    assert llm.last_call.fallback_used is (status != 200)
    if status != 200:
        assert any("AI provider is unavailable" in warning for warning in payload["warnings"])
