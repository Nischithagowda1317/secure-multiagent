from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class AgentResult:
    agent_id: str
    agent_name: str
    summary: str
    content: dict[str, Any] | list[Any] | str = field(default_factory=dict)
    sources: list[dict[str, Any]] = field(default_factory=list)
    confidence: float = 0.9
    warnings: list[str] = field(default_factory=list)

    def section(self) -> dict[str, Any]:
        return {
            "title": self.agent_name,
            "summary": self.summary,
            "content": self.content,
            "confidence": round(self.confidence, 4),
            "warnings": self.warnings,
        }
