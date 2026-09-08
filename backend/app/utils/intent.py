from __future__ import annotations

import re


_ACTION_VERB = r"(?:reassign|assign|move|change|reallocate|transfer|redistribute)"
_TASK_OBJECT = (
    r"(?:\bT\d{5}\b|\b(?:this|that|the|a|one|another)?\s*"
    r"(?:task|work|assignee|assignment)\b|\bit\b)"
)


def is_reassignment_topic(query: str) -> bool:
    """Return whether a request discusses assignment or reassignment."""
    lowered = query.lower()
    return bool(
        re.search(r"\breassign(?:ed|ing|ment)?\b", lowered)
        or re.search(r"\breallocat(?:e|ed|ing|ion)\b", lowered)
        or re.search(r"\b(?:change|move|transfer|redistribute)\b.{0,50}\b(?:task|work|assignee)\b", lowered)
        or re.search(r"\b(?:change|move|transfer|redistribute)\b.{0,50}\bT\d{5}\b", query, re.IGNORECASE)
        or re.search(r"\b(?:task allocation|assignment capacity)\b", lowered)
        or re.search(r"\bassign\b.{0,40}\btask\b", lowered)
    )


def is_reassignment_action(query: str) -> bool:
    """Require both a request-to-act construction and a task/action object.

    Nouns and passive forms such as ``reassignment`` and ``reassigned work``
    deliberately do not qualify. Questions asking who *could* take work are
    analysis, while polite requests asking the assistant to reassign are
    mutations.
    """
    text = query.strip()
    if not text or not is_reassignment_topic(text):
        return False

    request_to_act = bool(
        re.search(rf"^\s*(?:please\s+)?{_ACTION_VERB}\b", text, re.IGNORECASE)
        or re.search(
            rf"^\s*(?:can|could|would|will)\s+you\s+(?:please\s+)?{_ACTION_VERB}\b",
            text,
            re.IGNORECASE,
        )
        or re.search(
            rf"\b(?:i\s+(?:want|need|would like)\s+(?:you\s+)?to)\s+{_ACTION_VERB}\b",
            text,
            re.IGNORECASE,
        )
    )
    has_action_object = bool(re.search(_TASK_OBJECT, text, re.IGNORECASE))
    return request_to_act and has_action_object


def reassignment_read_workflow(query: str) -> str:
    """Choose workforce analysis for substantive questions, safe RAG otherwise."""
    lowered = query.lower()
    workforce_analysis = bool(
        re.search(
            r"\b(who|which|available|availability|capacity|suitable|eligible|"
            r"overloaded|workload|take|receive|member|members|employee|employees|"
            r"project|show|list|identify|recommend|should|need)\b",
            lowered,
        )
    )
    return "WFD003" if workforce_analysis else "WFD001"
