from __future__ import annotations

import pytest

from app.services.llm_service import sanitize_llm_response


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "Based on the provided JSON, the enterprise response is: "
            "Project Atlas is at risk.",
            "Project Atlas is at risk.",
        ),
        (
            "Based on the provided JSON:\n\nProject Atlas is at risk.",
            "Project Atlas is at risk.",
        ),
        (
            "Here is the enterprise response:\nNova is on track.",
            "Nova is on track.",
        ),
        (
            "Project Atlas is currently at risk.",
            "Project Atlas is currently at risk.",
        ),
        (
            "Project Atlas is at risk. Based on the provided data from last "
            "quarter, management increased capacity.",
            "Project Atlas is at risk. Based on the provided data from last "
            "quarter, management increased capacity.",
        ),
        (
            "Based on the supplied context:\n\n## Project Status\n- Progress: 58%",
            "## Project Status\n- Progress: 58%",
        ),
    ],
)
def test_sanitize_llm_response(raw: str, expected: str):
    assert sanitize_llm_response(raw) == expected


@pytest.mark.parametrize(
    "prefix",
    [
        "Based on the supplied data:",
        "According to the provided JSON:",
        "Based on the provided context:",
        "Based on the context provided:",
        "Here is the response:",
        "The enterprise response is:",
        "Using the supplied evidence:",
        "Based on the provided JSON, here is a concise, grounded enterprise response:",
        "Here is a concise, grounded enterprise response based on the provided JSON:",
    ],
)
def test_sanitizer_handles_supported_leading_variants_case_insensitively(prefix: str):
    raw = f"{prefix.swapcase()}\n\n## Status\n- Progress: 58%"
    assert sanitize_llm_response(raw) == "## Status\n- Progress: 58%"
