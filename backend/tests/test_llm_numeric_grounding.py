from __future__ import annotations

import asyncio

from app.services.llm_providers import (
    GenerationRequest,
    LLMProvider,
    OllamaProvider,
    ProviderResponse,
)
from app.services.llm_service import LLMService
from app.settings import Settings


def _settings() -> Settings:
    return Settings(
        llm_provider="ollama",
        llm_fallback_provider="extractive",
        ollama_base_url="http://ollama.test",
        ollama_model="llama3.1:8b",
        ollama_timeout_seconds=1,
    )


class NumericResponseProvider(LLMProvider):
    name = "ollama"
    model = "llama3.1:8b"

    def __init__(self, text: str):
        self.text = text
        self.requests: list[GenerationRequest] = []

    async def generate(self, request: GenerationRequest) -> ProviderResponse:
        self.requests.append(request)
        return ProviderResponse(self.text, self.name, self.model, 20)

    async def health_check(self) -> bool:
        return True


def _generate(text: str, content: dict, fallback: str = "Grounded fallback"):
    async def scenario():
        provider = NumericResponseProvider(text)
        service = LLMService(_settings(), provider=provider)
        answer = await service.synthesize(
            "Summarize the supplied metrics.",
            [],
            [{"title": "Metrics", "content": content}],
            fallback_text=fallback,
        )
        return answer, service.last_call, provider.requests[-1]

    return asyncio.run(scenario())


def test_percent_field_allows_integer_with_percent_format():
    answer, metrics, request = _generate(
        "Current progress is 58%.", {"current_progress_percent": 58}
    )

    assert answer == "Current progress is 58%."
    assert metrics is not None and metrics.fallback_used is False
    assert metrics.numeric_grounding_status == "passed_with_normalized_matches"
    assert {
        "field": "sections[0].content.current_progress_percent",
        "value": 58,
        "unit": "%",
    } in request.allowed_numeric_facts


def test_equivalent_decimal_percent_format_is_allowed():
    answer, metrics, _ = _generate(
        "Alaa has 46.10% workload.", {"total_workload_percent": 46.1}
    )

    assert answer == "Alaa has 46.10% workload."
    assert metrics is not None and metrics.fallback_used is False
    assert metrics.normalized_numeric_match_count == 1


def test_numeric_range_hyphen_is_not_a_negative_claim():
    answer, metrics, _ = _generate(
        "Discount approval is required in the 10%-20% range.",
        {"lower_discount_percent": 10, "upper_discount_percent": 20},
    )

    assert answer == "Discount approval is required in the 10%-20% range."
    assert metrics is not None and metrics.fallback_used is False


def test_genuine_negative_value_still_requires_explicit_evidence():
    answer, metrics, _ = _generate(
        "The variance is -20%.", {"variance_percent": 20}
    )

    assert answer == "Grounded fallback"
    assert metrics is not None and metrics.fallback_used is True
    assert str(metrics.error_status).startswith("unsupported_numeric_claim:-20%")


def test_derived_profit_margin_is_rejected_without_backend_margin():
    answer, metrics, _ = _generate(
        "Profit margin is 8%.",
        {"sales_usd": 100, "profit_usd": 8},
    )

    assert answer == "Grounded fallback"
    assert metrics is not None and metrics.fallback_used is True
    assert metrics.numeric_grounding_status == "unsupported_derived_metric"
    assert str(metrics.error_status).startswith("unsupported_derived_metric:8%")


def test_backend_supplied_profit_margin_percent_is_allowed():
    answer, metrics, _ = _generate(
        "Profit margin is 8%.",
        {"sales_usd": 100, "profit_usd": 8, "profit_margin_percent": 8},
    )

    assert answer == "Profit margin is 8%."
    assert metrics is not None and metrics.fallback_used is False


def test_ids_dates_task_numbers_and_versions_are_not_business_numeric_claims():
    answer, metrics, request = _generate(
        "Task T00064 is assigned to E0013 as of 2026-08-28 using model llama3.1.",
        {
            "task_id": "T00064",
            "employee_id": "E0013",
            "snapshot_date": "2026-08-28",
            "model_version": "llama3.1",
        },
    )

    assert answer.startswith("Task T00064")
    assert metrics is not None and metrics.fallback_used is False
    assert metrics.numeric_grounding_status == "no_numeric_claims"
    assert request.allowed_numeric_facts == []


def test_unsupported_numeric_value_is_rejected_as_real_hallucination():
    answer, metrics, _ = _generate(
        "The result is 91.62%.", {"current_progress_percent": 58}
    )

    assert answer == "Grounded fallback"
    assert metrics is not None and metrics.fallback_used is True
    assert metrics.numeric_grounding_status == "real_hallucination_rejection"
    assert str(metrics.error_status).startswith("unsupported_numeric_claim:91.62%")


def test_currency_symbol_and_grouping_are_safe_equivalent_formats():
    answer, metrics, request = _generate(
        "Sales total $740,000.", {"sales_usd": 740000}
    )
    prompt = OllamaProvider._build_prompt(request)

    assert answer == "Sales total $740,000."
    assert metrics is not None and metrics.fallback_used is False
    assert '"allowed_numeric_facts"' in prompt
    assert '"unit":"USD"' in prompt
