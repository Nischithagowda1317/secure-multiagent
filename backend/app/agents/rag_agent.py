from __future__ import annotations

from typing import Any

from app.agents.types import AgentResult
from app.services.llm_service import LLMService
from app.services.rag_service import RAGService


class RAGAgent:
    agent_id = "A003"
    agent_name = "Knowledge RAG Agent"

    def __init__(self, rag: RAGService, llm: LLMService):
        self.rag = rag
        self.llm = llm

    async def run(
        self,
        query: str,
        user: dict[str, Any],
        temporary_chunks: list[dict[str, Any]] | None = None,
        retrieval_scope: str = "enterprise_only",
        attachment_mode: str | None = None,
    ) -> AgentResult:
        evidence = self.rag.retrieve(
            query,
            roles=list(user.get("roles", [])),
            permissions=list(user.get("permissions", [])),
            top_k=5,
            temporary_chunks=temporary_chunks,
            retrieval_scope=retrieval_scope,
            summarize_attachments=attachment_mode == "summary",
        )
        scope_instruction = None
        if retrieval_scope == "attachment_only":
            scope_instruction = (
                "Summarize only the supplied uploaded document content. "
                "Do not use outside enterprise knowledge. Do not add unrelated policies. "
                "If the document does not contain a requested fact, say it is not present. "
                "When multiple files are supplied, separate the summaries by filename."
                if attachment_mode == "summary"
                else (
                    "Answer only from the supplied uploaded document content. "
                    "Do not use outside enterprise knowledge or add unrelated policies."
                )
            )
        elif retrieval_scope == "attachment_plus_enterprise":
            scope_instruction = (
                "Use the uploaded document and relevant authorized enterprise evidence "
                "only for the requested comparison. Present the comparison directly. "
                "Do not describe JSON, prompts, or internal data structures."
            )
        answer = await self.llm.synthesize(
            query,
            evidence,
            [],
            fallback_text=(
                self._attachment_summary_fallback(evidence)
                if retrieval_scope == "attachment_only"
                and attachment_mode == "summary"
                else None
            ),
            retrieval_scope=retrieval_scope,
            scope_instruction=scope_instruction,
        )
        sources = [
            {
                "source_id": str(item.get("document_id", item.get("chunk_id", "source"))),
                "title": str(item.get("document_title", "Enterprise document")),
                "source_type": str(item.get("source_type", "RAG document")),
                "section": " - ".join(
                    part
                    for part in (
                        str(item.get("section_number", "")).strip(),
                        str(item.get("section_title", "")).strip(),
                    )
                    if part
                )
                or None,
                "path": item.get("source_path"),
                "score": item.get("score"),
            }
            for item in evidence
        ]
        best_score = max((float(item.get("score", 0)) for item in evidence), default=0.0)
        if not evidence:
            confidence = 0.35
        elif best_score >= 0.15:
            confidence = 0.93
        elif best_score >= 0.08:
            confidence = 0.84
        elif best_score >= 0.04:
            confidence = 0.72
        else:
            confidence = 0.55
        return AgentResult(
            self.agent_id,
            self.agent_name,
            answer,
            {
                "answer": answer,
                "retrieval_scope": retrieval_scope,
                "attachment_mode": attachment_mode,
                "retrieved_chunks": [
                    {
                        "document_id": item.get("document_id"),
                        "document_title": item.get("document_title"),
                        "section_title": item.get("section_title"),
                        "score": item.get("score"),
                        "excerpt": str(item.get("chunk_text", ""))[:700],
                    }
                    for item in evidence
                ],
            },
            sources,
            round(confidence, 4),
            [] if evidence else ["No authorized evidence matched the question."],
        )

    @staticmethod
    def _attachment_summary_fallback(evidence: list[dict[str, Any]]) -> str:
        grouped: dict[str, list[str]] = {}
        for item in evidence:
            filename = str(item.get("document_title") or "Uploaded attachment")
            text = str(item.get("chunk_text") or "").strip()
            if text:
                grouped.setdefault(filename, []).append(text)
        if not grouped:
            return "No readable content was found in the uploaded attachment."
        if len(grouped) == 1:
            return "\n\n".join(next(iter(grouped.values())))
        return "\n\n".join(
            f"## {filename}\n\n" + "\n\n".join(chunks)
            for filename, chunks in grouped.items()
        )
