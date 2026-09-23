from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

import httpx

from app.services.llm_providers import (
    ExtractiveProvider,
    GenerationRequest,
    LLMProvider,
    OpenAIProvider,
)
from app.settings import Settings
from app.utils.json_tools import json_safe


logger = logging.getLogger(__name__)


_LEADING_META_PREFACE = re.compile(
    r"""
    ^\s*(?:\*\*|__)?\s*(?:
        based\s+on\s+(?:the\s+)?
            (?:(?:provided|supplied)\s+(?:json|data|context|evidence)|
               (?:json|data|context|evidence)\s+(?:provided|supplied))
            (?:\s*,\s*(?:(?:the\s+)?(?:requested\s+)?enterprise\s+response\s+is|
                         here\s+is\s+(?:a|the)?\s*(?:concise\s*,?\s*)?
                         (?:grounded\s+)?enterprise\s+response))?
      | according\s+to\s+(?:the\s+)?(?:provided|supplied)\s+
            (?:json|data|context|evidence)
      | here\s+is\s+(?:a|the)?\s*(?:requested\s+)?
            (?:concise\s*,?\s*)?(?:grounded\s+)?(?:enterprise\s+)?response
            (?:\s+based\s+on\s+(?:the\s+)?
                (?:(?:provided|supplied)\s+(?:json|data|context|evidence)|
                   (?:json|data|context|evidence)\s+(?:provided|supplied)))?
      | (?:the\s+)?(?:requested\s+)?enterprise\s+response\s+is
      | using\s+(?:the\s+)?(?:provided|supplied)\s+
            (?:json|data|context|evidence)
    )\s*(?:\*\*|__)?\s*:\s*
    """,
    re.IGNORECASE | re.VERBOSE,
)


def sanitize_llm_response(text: str) -> str:
    """Remove recognized meta-prefaces only when they lead the response."""
    sanitized = str(text).strip()
    for _ in range(2):
        match = _LEADING_META_PREFACE.match(sanitized)
        if not match:
            break
        sanitized = sanitized[match.end() :].lstrip()
    return sanitized


_NUMBER_PATTERN = r"[-+]?(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?"
_NUMERIC_MENTION = re.compile(
    rf"(?P<currency_prefix>[$]\s*(?P<currency_prefix_value>{_NUMBER_PATTERN}))"
    rf"|(?P<percent>(?P<percent_value>{_NUMBER_PATTERN})\s*(?:%|percent(?:age)?\b))"
    rf"|(?P<currency_suffix>(?P<currency_suffix_value>{_NUMBER_PATTERN})\s*(?:USD|dollars?\b))"
    rf"|(?P<number>{_NUMBER_PATTERN})",
    re.IGNORECASE,
)
_DATE_OR_VERSION = re.compile(
    r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b"
    r"|\b(?:version|ver\.?|v)\s*\d+(?:\.\d+)+\b"
    r"|\b\d+(?:\.\d+){2,}\b",
    re.IGNORECASE,
)
_ALPHANUMERIC_IDENTIFIER = re.compile(
    r"\b(?=[A-Za-z0-9_.:-]*[A-Za-z])(?=[A-Za-z0-9_.:-]*\d)"
    r"[A-Za-z][A-Za-z0-9_.:-]*\b"
)
_NON_BUSINESS_NUMERIC_FIELD = re.compile(
    r"(?:^|_)(?:id|date|timestamp|version|sequence)(?:$|_)", re.IGNORECASE
)


@dataclass(frozen=True)
class NumericMention:
    value: Decimal
    unit: str
    raw: str


@dataclass(frozen=True)
class GroundingGuardResult:
    error_status: str | None
    numeric_status: str
    normalized_match_count: int = 0


def _decimal(value: Any) -> Decimal | None:
    try:
        return Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        return None


def _json_number(value: Decimal) -> int | float:
    return int(value) if value == value.to_integral_value() else float(value)


def _field_unit(field: str) -> str:
    normalized = field.lower()
    if "percent" in normalized or normalized.endswith(("_pct", ".pct")):
        return "%"
    if "usd" in normalized or "salary" in normalized:
        return "USD"
    if normalized.endswith(("_ms", ".ms")):
        return "ms"
    if "hour" in normalized:
        return "hours"
    if normalized.endswith(("_count", ".count")) or "count" in normalized:
        return "count"
    return "number"


def _mask_non_business_numbers(text: str) -> str:
    masked = text
    for pattern in (_DATE_OR_VERSION, _ALPHANUMERIC_IDENTIFIER):
        masked = pattern.sub(lambda match: " " * len(match.group(0)), masked)
    # A hyphen directly joining two digits is a range separator (for example,
    # 10-20%), not the sign of the upper bound. Keep genuine leading negative
    # values intact so they still require an explicitly authorized fact.
    masked = re.sub(r"(?<=\d)-(?=\d)|(?<=%)-(?=\d)", " ", masked)
    return masked


def _numeric_mentions(text: str) -> list[NumericMention]:
    mentions: list[NumericMention] = []
    for match in _NUMERIC_MENTION.finditer(_mask_non_business_numbers(text)):
        if match.group("currency_prefix"):
            raw_value = match.group("currency_prefix_value")
            unit = "USD"
        elif match.group("percent"):
            raw_value = match.group("percent_value")
            unit = "%"
        elif match.group("currency_suffix"):
            raw_value = match.group("currency_suffix_value")
            unit = "USD"
        else:
            raw_value = match.group("number")
            unit = "number"
        value = _decimal(raw_value)
        if value is not None:
            mentions.append(NumericMention(value=value, unit=unit, raw=match.group(0)))
    return mentions


def build_allowed_numeric_facts(
    evidence: list[dict[str, Any]],
    structured_sections: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build field-aware numeric facts from already-authorized context."""
    facts: list[dict[str, Any]] = []
    seen: set[tuple[str, Decimal, str]] = set()

    def add(field: str, value: Decimal, unit: str) -> None:
        key = (field, value.normalize(), unit)
        if key in seen:
            return
        seen.add(key)
        facts.append({"field": field, "value": _json_number(value), "unit": unit})

    def walk(value: Any, path: str) -> None:
        field = path.rsplit(".", 1)[-1]
        if _NON_BUSINESS_NUMERIC_FIELD.search(field):
            return
        if isinstance(value, bool) or value is None:
            return
        if isinstance(value, (int, float)):
            number = _decimal(value)
            if number is not None:
                add(path, number, _field_unit(path))
            return
        if isinstance(value, dict):
            for key, child in value.items():
                walk(child, f"{path}.{key}" if path else str(key))
            return
        if isinstance(value, (list, tuple)):
            for index, child in enumerate(value):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(value, str):
            stripped = value.strip()
            direct = _decimal(stripped) if re.fullmatch(_NUMBER_PATTERN, stripped) else None
            if direct is not None:
                add(path, direct, _field_unit(path))
                return
            for index, mention in enumerate(_numeric_mentions(value)):
                add(f"{path}.mention[{index}]", mention.value, mention.unit)

    for index, item in enumerate(evidence[:6]):
        chunk_text = item.get("chunk_text")
        if isinstance(chunk_text, str):
            walk(chunk_text, f"evidence[{index}].chunk_text")
    for index, section in enumerate(structured_sections):
        walk(section.get("summary"), f"sections[{index}].summary")
        walk(section.get("content"), f"sections[{index}].content")
    return facts


@dataclass(frozen=True)
class LLMCallMetrics:
    provider: str
    model: str | None
    latency_ms: int
    fallback_used: bool
    prompt_token_approx: int
    response_length: int
    error_status: str | None
    numeric_grounding_status: str
    normalized_numeric_match_count: int


class LLMService:
    """Provider facade that keeps local generation optional and fail-safe."""

    def __init__(
        self,
        settings: Settings,
        *,
        provider: LLMProvider | None = None,
        fallback_provider: LLMProvider | None = None,
    ) -> None:
        self.settings = settings
        if settings.llm_fallback_provider != "extractive" and fallback_provider is None:
            logger.warning(
                "Unsupported fallback provider '%s'; using extractive.",
                settings.llm_fallback_provider,
            )
        self.fallback_provider = fallback_provider or ExtractiveProvider()
        self.provider = provider or self._build_provider(settings.llm_provider)
        self._last_call: LLMCallMetrics | None = None
        self._call_count = 0
        self._fallback_count = 0
        self._error_count = 0
        self._hallucination_rejection_count = 0
        self._unsupported_derived_metric_count = 0
        self._normalized_numeric_match_count = 0

    def _build_provider(self, provider_name: str) -> LLMProvider:
        if provider_name == "openai":
            return OpenAIProvider(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
                timeout_seconds=self.settings.openai_timeout_seconds,
            )
        if provider_name != "extractive":
            logger.warning(
                "Unknown LLM provider '%s'; using the extractive provider.", provider_name
            )
        return ExtractiveProvider()

    @property
    def generative_enabled(self) -> bool:
        return self.provider.name == "openai"

    @property
    def last_call(self) -> LLMCallMetrics | None:
        return self._last_call

    async def synthesize(
        self,
        query: str,
        evidence: list[dict[str, Any]],
        structured_sections: list[dict[str, Any]],
        *,
        fallback_text: str | None = None,
        retrieval_scope: str = "enterprise_only",
        scope_instruction: str | None = None,
    ) -> str:
        request = GenerationRequest(
            query=query,
            evidence=evidence,
            structured_sections=structured_sections,
            allowed_numeric_facts=build_allowed_numeric_facts(
                evidence, structured_sections
            ),
            retrieval_scope=retrieval_scope,
            scope_instruction=scope_instruction,
            fallback_text=fallback_text,
        )
        started = time.perf_counter()
        fallback_used = False
        error_status: str | None = None
        prompt_token_approx = 0
        numeric_grounding_status = "not_checked"
        normalized_numeric_match_count = 0
        try:
            response = await self.provider.generate(request)
            prompt_token_approx = response.prompt_token_approx
            answer = sanitize_llm_response(response.text)
            if not answer:
                raise ValueError("LLM response contained only a meta-preface")
            if self.provider.name != "extractive":
                guard = self._grounding_guard(answer, request)
                numeric_grounding_status = guard.numeric_status
                normalized_numeric_match_count = guard.normalized_match_count
                if guard.error_status:
                    raise UngroundedResponseError(guard.error_status)
        except Exception as exc:  # provider failures must not break the workflow
            fallback_used = self.provider.name != self.fallback_provider.name
            error_status = self._error_status(exc)
            logger.warning(
                "LLM provider failed; using fallback provider "
                "(provider=%s model=%s error=%s).",
                self.provider.name,
                self.provider.model,
                error_status,
            )
            response = await self.fallback_provider.generate(request)
            answer = sanitize_llm_response(response.text)

        latency_ms = int((time.perf_counter() - started) * 1000)
        self._call_count += 1
        self._fallback_count += int(fallback_used)
        self._error_count += int(error_status is not None)
        self._hallucination_rejection_count += int(
            numeric_grounding_status == "real_hallucination_rejection"
        )
        self._unsupported_derived_metric_count += int(
            numeric_grounding_status == "unsupported_derived_metric"
        )
        self._normalized_numeric_match_count += normalized_numeric_match_count
        self._last_call = LLMCallMetrics(
            provider=self.provider.name,
            model=self.provider.model,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            prompt_token_approx=prompt_token_approx,
            response_length=len(answer),
            error_status=error_status,
            numeric_grounding_status=numeric_grounding_status,
            normalized_numeric_match_count=normalized_numeric_match_count,
        )
        logger.info(
            "LLM generation completed provider=%s model=%s latency_ms=%d "
            "fallback_used=%s prompt_token_approx=%d response_length=%d error=%s "
            "numeric_grounding_status=%s normalized_numeric_matches=%d",
            self.provider.name,
            self.provider.model,
            latency_ms,
            fallback_used,
            prompt_token_approx,
            len(answer),
            error_status or "none",
            numeric_grounding_status,
            normalized_numeric_match_count,
        )
        return answer

    async def health_check(self) -> dict[str, Any]:
        available = await self.provider.health_check()
        return {
            "llm_provider": self.provider.name,
            "llm_available": available,
            "llm_model": self.provider.model,
            "fallback_provider": self.fallback_provider.name,
        }

    def metrics(self) -> dict[str, Any]:
        return {
            "provider": self.provider.name,
            "model": self.provider.model,
            "fallback_provider": self.fallback_provider.name,
            "call_count": self._call_count,
            "fallback_count": self._fallback_count,
            "error_count": self._error_count,
            "hallucination_rejection_count": self._hallucination_rejection_count,
            "unsupported_derived_metric_count": self._unsupported_derived_metric_count,
            "normalized_numeric_match_count": self._normalized_numeric_match_count,
            "last_call": asdict(self._last_call) if self._last_call else None,
        }

    @staticmethod
    def extractive_answer(
        query: str,
        evidence: list[dict[str, Any]],
        structured_sections: list[dict[str, Any]],
    ) -> str:
        """Compatibility entry point for existing callers and tests."""
        return ExtractiveProvider.extractive_answer(query, evidence, structured_sections)

    @staticmethod
    def _grounding_guard(
        answer: str, request: GenerationRequest
    ) -> GroundingGuardResult:
        """Validate business numbers against backend-supplied field/unit facts."""
        facts: list[tuple[Decimal, str]] = []
        for fact in request.allowed_numeric_facts:
            value = _decimal(fact.get("value"))
            if value is not None:
                facts.append((value, str(fact.get("unit") or "number")))

        mentions = _numeric_mentions(answer)
        normalized_matches = 0
        unsupported: list[NumericMention] = []
        derived: list[NumericMention] = []
        for mention in mentions:
            same_value = [(value, unit) for value, unit in facts if value == mention.value]
            if mention.unit == "number":
                compatible = same_value
            else:
                compatible = [
                    (value, unit) for value, unit in same_value if unit == mention.unit
                ]
            if compatible:
                canonical = format(mention.value.normalize(), "f")
                raw_number_match = re.search(_NUMBER_PATTERN, mention.raw)
                raw_number = (
                    raw_number_match.group(0).replace(",", "")
                    if raw_number_match
                    else canonical
                )
                if mention.unit != "number" or raw_number != canonical:
                    normalized_matches += 1
                continue
            if same_value and mention.unit in {"%", "USD"}:
                derived.append(mention)
            else:
                unsupported.append(mention)

        if derived:
            values = ",".join(mention.raw.strip() for mention in derived[:5])
            return GroundingGuardResult(
                error_status=f"unsupported_derived_metric:{values}",
                numeric_status="unsupported_derived_metric",
                normalized_match_count=normalized_matches,
            )
        if unsupported:
            values = ",".join(mention.raw.strip() for mention in unsupported[:5])
            return GroundingGuardResult(
                error_status=f"unsupported_numeric_claim:{values}",
                numeric_status="real_hallucination_rejection",
                normalized_match_count=normalized_matches,
            )

        numeric_status = (
            "no_numeric_claims"
            if not mentions
            else (
                "passed_with_normalized_matches"
                if normalized_matches
                else "passed_exact"
            )
        )
        context = json.dumps(
            json_safe(
                {
                    "query": request.query,
                    "evidence": request.evidence,
                    "structured_sections": request.structured_sections,
                }
            ),
            ensure_ascii=False,
        )
        execution_claims = (
            "has been executed",
            "was executed",
            "successfully executed",
            "has been approved",
            "was approved",
            "is approved",
            "has been rejected",
            "was rejected",
            "is rejected",
        )
        lowered_answer = answer.lower()
        lowered_context = context.lower()
        for claim in execution_claims:
            if claim in lowered_answer and claim not in lowered_context:
                return GroundingGuardResult(
                    error_status="unsupported_action_claim",
                    numeric_status=numeric_status,
                    normalized_match_count=normalized_matches,
                )
        return GroundingGuardResult(
            error_status=None,
            numeric_status=numeric_status,
            normalized_match_count=normalized_matches,
        )

    @staticmethod
    def _numbers(text: str) -> list[str]:
        return [format(item.value.normalize(), "f") for item in _numeric_mentions(text)]

    @staticmethod
    def _error_status(exc: Exception) -> str:
        if isinstance(exc, UngroundedResponseError):
            return str(exc)
        if isinstance(exc, httpx.HTTPStatusError):
            # API error messages may echo credentials or supplied input. Keep
            # only the HTTP status and machine-readable classification fields.
            details = [f"HTTPStatusError: HTTP {exc.response.status_code}"]
            try:
                body = exc.response.json()
            except ValueError:
                body = None
            error = body.get("error") if isinstance(body, dict) else None
            if isinstance(error, dict):
                for field in ("code", "type"):
                    value = error.get(field)
                    if isinstance(value, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,79}", value):
                        details.append(f"{field}={value}")
            return " ".join(details)
        name = type(exc).__name__
        message = str(exc).strip()
        return f"{name}: {message[:160]}" if message else name


class UngroundedResponseError(ValueError):
    pass
