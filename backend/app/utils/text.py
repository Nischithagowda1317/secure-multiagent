from __future__ import annotations

import re
from collections.abc import Iterable


_WORD_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_\-']+")


def normalize_text(value: str) -> str:
    return " ".join(str(value).strip().lower().split())


def tokenize(value: str) -> list[str]:
    normalized = (value or "").replace("-", " ").replace("_", " ")
    return [token.lower() for token in _WORD_RE.findall(normalized)]


def sentence_split(text: str) -> list[str]:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if not cleaned:
        return []
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", cleaned) if part.strip()]


def compact_dict(mapping: dict) -> dict:
    return {key: value for key, value in mapping.items() if value not in (None, "", [], {})}


def pointwise_answer(text: str) -> str:
    """Format final answers consistently, including deterministic fallbacks."""
    points: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        marker = re.match(r"^(?:[-*+\u2022]|\d+[.)])\s+", line)
        if marker:
            # Keep existing points intact and avoid duplicate bullet markers.
            points.append(line[marker.end():])
        else:
            line = re.sub(r"^#{1,6}\s+", "", line)
            line_points: list[str] = []
            for sentence in sentence_split(line):
                # Keep common abbreviations and initials with their continuation.
                if line_points and re.search(
                    r"\b(?:Mr|Mrs|Ms|Dr|Prof|Sr|Jr|e\.g|i\.e|[A-Z])\.$", line_points[-1]
                ):
                    line_points[-1] += " " + sentence
                else:
                    line_points.append(sentence)
            points.extend(line_points)
    return "\n".join(f"- {point}" for point in points if point)


def pipe_values(value: object) -> list[str]:
    if value is None:
        return []
    text = str(value)
    if text.lower() == "nan":
        return []
    return [part.strip() for part in text.split("|") if part.strip()]


def first_match(text: str, values: Iterable[str]) -> str | None:
    lowered = normalize_text(text)
    matches = [value for value in values if normalize_text(value) in lowered]
    return max(matches, key=len) if matches else None
